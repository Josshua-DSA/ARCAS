"""Latih FOMC-RoBERTa pada korpus FOMC (P0-1).

Resep mengikuti rilis upstream yang menghasilkan checkpoint terbaik di
Hugging Face (`gtfintechlab/FOMC-RoBERTa`, Shah/Paturi/Chava, ACL 2023):
`roberta-large` + sequence classification 3 kelas pada korpus kalimat FOMC
(label 0=dovish, 1=hawkish, 2=neutral).

Jalankan dari akar repo:

    python -m scripts.train_fomc_roberta                    # resep upstream
    python -m scripts.train_fomc_roberta --base roberta-base   # hemat VRAM
    python -m scripts.train_fomc_roberta --epochs 3 --batch-size 8 \
        --grad-accum 4

Alur:
  1. muat & bersihkan korpus (`model/fomc/src/data_loader.py`),
  2. split train/val stratified dari split train (test holdout TIDAK disentuh),
  3. fine-tune penuh (semua bobot) dengan fp16 + gradient accumulation,
  4. pilih checkpoint terbaik menurut macro-F1 validation,
  5. kalibrasi temperature pada validation,
  6. tulis bobot + `metrics.json` + `temperature.json` ke `model/fomc/weights/`.

Kenapa macro-F1, bukan accuracy: sama dengan track XAU — kelas `neutral`
minoritas, sehingga model yang mengabaikannya tetap terlihat bagus di
accuracy. Macro-F1 memberi bobot sama ke tiap kelas.

Kenapa `roberta-large`: itu yang dipakai checkpoint upstream yang menjadi
acuan angka pembanding. `--base roberta-base` disediakan untuk GPU kecil;
hasilnya bukan reproduksi upstream dan tidak boleh dibandingkan langsung.

Peringatan VRAM: `roberta-large` dengan `batch_size=8`, `max_length=256`,
fp16 membutuhkan ~6-7 GiB. Pada GPU 6 GiB pakai `--batch-size 4
--grad-accum 4` (efektif tetap 16) atau `--base roberta-base`.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from model.fomc.src.calibrator import TemperatureScaler
from model.fomc.src.data_loader import (
    LABEL_TO_STANCE,
    get_fomc_texts_and_labels,
    load_fomc_test_holdout,
    load_fomc_train_val_split,
)

ROOT = Path(__file__).resolve().parents[1]

#: Checkpoint dasar. `roberta-large` = resep upstream.
UPSTREAM_BASE = "roberta-large"

STANCES = [LABEL_TO_STANCE[i] for i in range(3)]  # ["dovish", "hawkish", "neutral"]

DEFAULT_OUTPUT_DIR = Path("model/fomc/weights/roberta")
DEFAULT_METRICS_PATH = Path("model/fomc/weights/metrics.json")
DEFAULT_TEMPERATURE_PATH = Path("model/fomc/weights/temperature.json")


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    from sklearn.metrics import f1_score

    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def _class_report(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Presisi/recall/F1 per kelas — tanpa ini, rata-rata menyembunyikan neutral."""
    from sklearn.metrics import precision_recall_fscore_support

    prec, rec, f1, sup = precision_recall_fscore_support(
        y_true,
        y_pred,
        labels=[0, 1, 2],
        zero_division=0,  # type: ignore[arg-type]
    )
    report: dict[str, Any] = {}
    for i, stance in enumerate(STANCES):
        report[stance] = {
            "precision": float(prec[i]),
            "recall": float(rec[i]),
            "f1": float(f1[i]),
            "support": int(sup[i]),
        }
    return report


def _resolve_device(requested: str | None) -> str:
    import torch

    if requested:
        return requested
    return "cuda" if torch.cuda.is_available() else "cpu"


def train(
    base: str = UPSTREAM_BASE,
    epochs: int = 5,
    batch_size: int = 8,
    grad_accum: int = 2,
    lr: float = 1e-5,
    max_length: int = 256,
    val_ratio: float = 0.10,
    seed: int = 5768,
    device: str | None = None,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    metrics_path: Path | str = DEFAULT_METRICS_PATH,
    temperature_path: Path | str = DEFAULT_TEMPERATURE_PATH,
    train_path: Path | str | None = None,
    test_path: Path | str | None = None,
) -> dict[str, Any]:
    import torch
    from torch.optim import AdamW
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )

    dev = _resolve_device(device)
    print(
        f"device={dev} | base={base} | epochs={epochs} | "
        f"batch={batch_size} x accum={grad_accum} | max_len={max_length}"
    )

    # --- 1. data ---
    kwargs: dict[str, Any] = {"val_ratio": val_ratio, "seed": seed}
    if train_path is not None:
        kwargs["path"] = train_path
    df_train, df_val = load_fomc_train_val_split(**kwargs)
    tr_texts, tr_labels = get_fomc_texts_and_labels(df_train)
    va_texts, va_labels = get_fomc_texts_and_labels(df_val)
    print(f"train={len(tr_texts)} val={len(va_texts)}")

    tokenizer = AutoTokenizer.from_pretrained(base)
    model = AutoModelForSequenceClassification.from_pretrained(base, num_labels=3)
    model.to(dev)

    class _DS(Dataset):  # type: ignore[misc]
        def __init__(self, texts: list[str], labels: list[int]) -> None:
            self.texts = texts
            self.labels = labels

        def __len__(self) -> int:
            return len(self.texts)

        def __getitem__(self, idx: int) -> dict[str, Any]:
            enc = tokenizer(
                self.texts[idx],
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_tensors="pt",
            )
            item = {k: v.squeeze(0) for k, v in enc.items()}
            item["labels"] = torch.tensor(int(self.labels[idx]), dtype=torch.long)
            return item

    dl_tr = DataLoader(_DS(tr_texts, tr_labels), batch_size=batch_size, shuffle=True)
    dl_va = DataLoader(_DS(va_texts, va_labels), batch_size=batch_size, shuffle=False)

    optim = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    steps_per_epoch = max(1, len(dl_tr) // max(1, grad_accum))
    total_steps = steps_per_epoch * epochs
    sched = get_linear_schedule_with_warmup(
        optim, num_warmup_steps=max(1, int(0.06 * total_steps)), num_training_steps=total_steps
    )
    # fp16 hanya di CUDA; di CPU autocast "cuda" akan jadi no-op yang
    # membingungkan, jadi dinonaktifkan eksplisit.
    use_amp = dev == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    best_f1 = -1.0
    best_state: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []

    for ep in range(1, epochs + 1):
        model.train()
        running = 0.0
        optim.zero_grad(set_to_none=True)
        for step, batch in enumerate(dl_tr, start=1):
            batch = {k: v.to(dev) for k, v in batch.items()}
            with torch.amp.autocast("cuda", enabled=use_amp):
                loss = model(**batch).loss / grad_accum
            scaler.scale(loss).backward()
            running += float(loss.item()) * grad_accum

            if step % grad_accum == 0 or step == len(dl_tr):
                scaler.unscale_(optim)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optim)
                scaler.update()
                sched.step()
                optim.zero_grad(set_to_none=True)

            if step % 50 == 0:
                print(f"  ep{ep} step {step}/{len(dl_tr)} loss={running / step:.4f}")

        # --- validasi ---
        model.eval()
        preds: list[int] = []
        with torch.no_grad():
            for batch in dl_va:
                batch = {k: v.to(dev) for k, v in batch.items()}
                logits = model(
                    input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]
                ).logits
                preds.extend(logits.argmax(dim=-1).cpu().tolist())
        y_pred = np.array(preds)
        y_true = np.array(va_labels)
        f1 = _macro_f1(y_true, y_pred)
        acc = float((y_pred == y_true).mean())
        history.append(
            {
                "epoch": ep,
                "train_loss": running / max(1, len(dl_tr)),
                "val_macro_f1": f1,
                "val_accuracy": acc,
            }
        )
        print(
            f"epoch {ep}: loss={running / max(1, len(dl_tr)):.4f} "
            f"val_macroF1={f1:.4f} val_acc={acc:.4f}"
        )

        if f1 > best_f1:
            best_f1 = f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            print(f"  -> checkpoint terbaik (macro-F1={f1:.4f})")

    if best_state is not None:
        model.load_state_dict(best_state)

    # --- simpan bobot ---
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"bobot disimpan ke {out_dir}")

    # --- kalibrasi temperature pada validation ---
    model.eval()
    val_logits: list[np.ndarray] = []
    with torch.no_grad():
        for batch in dl_va:
            batch = {k: v.to(dev) for k, v in batch.items()}
            lg = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
            val_logits.append(lg.cpu().numpy())
    logits_arr = np.vstack(val_logits)

    # `fit()` sudah menghitung ece_pre/ece_post sendiri; jangan hitung ulang
    # dengan urutan argumen yang mudah terbalik (probs dulu, baru labels).
    scaler_t = TemperatureScaler()
    scaler_t.fit(logits_arr, list(map(int, np.asarray(va_labels, dtype=np.int64))))
    scaler_t.save(temperature_path)
    print(
        f"temperature T={scaler_t.temperature:.4f} "
        f"(ECE {scaler_t.ece_pre:.4f} -> {scaler_t.ece_post:.4f})"
    )

    # --- evaluasi holdout (test TIDAK dipakai untuk memilih checkpoint) ---
    holdout: dict[str, Any] = {}
    try:
        test_kwargs: dict[str, Any] = {}
        if test_path is not None:
            test_kwargs["path"] = test_path
        df_test = load_fomc_test_holdout(**test_kwargs)
        te_texts, te_labels = get_fomc_texts_and_labels(df_test)
        dl_te = DataLoader(_DS(te_texts, te_labels), batch_size=batch_size, shuffle=False)
        probs_out: list[np.ndarray] = []
        with torch.no_grad():
            for batch in dl_te:
                batch = {k: v.to(dev) for k, v in batch.items()}
                lg = model(
                    input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]
                ).logits
                probs_out.append(scaler_t.predict_proba(lg.cpu().numpy()))
        probs_arr = np.vstack(probs_out)
        te_pred = probs_arr.argmax(axis=1)
        te_true = np.array(te_labels)
        holdout = {
            "n": int(len(te_true)),
            "accuracy": float((te_pred == te_true).mean()),
            "macro_f1": _macro_f1(te_true, te_pred),
            "per_class": _class_report(te_true, te_pred),
        }
        print(f"holdout: acc={holdout['accuracy']:.4f} macroF1={holdout['macro_f1']:.4f}")
    except Exception as exc:  # noqa: BLE001
        print(f"peringatan: evaluasi holdout dilewati ({exc})")

    metrics: dict[str, Any] = {
        "model": "fomc_roberta",
        "base_checkpoint": base,
        "upstream_reference": "gtfintechlab/FOMC-RoBERTa",
        "is_upstream_recipe": base == UPSTREAM_BASE,
        "label_map": {str(k): v for k, v in LABEL_TO_STANCE.items()},
        "hyperparameters": {
            "epochs": epochs,
            "batch_size": batch_size,
            "grad_accum": grad_accum,
            "effective_batch_size": batch_size * grad_accum,
            "learning_rate": lr,
            "max_length": max_length,
            "weight_decay": 0.01,
            "warmup_fraction": 0.06,
            "seed": seed,
            "fp16": use_amp,
        },
        "train_size": len(tr_texts),
        "val_size": len(va_texts),
        "best_val_macro_f1": best_f1,
        "history": history,
        "temperature": scaler_t.temperature,
        "ece_pre": scaler_t.ece_pre,
        "ece_post": scaler_t.ece_post,
        "holdout": holdout,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    mp = Path(metrics_path)
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"metrik disimpan ke {mp}")
    return metrics


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--base", default=UPSTREAM_BASE, help=f"checkpoint dasar (default: {UPSTREAM_BASE})"
    )
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=8)
    ap.add_argument(
        "--grad-accum",
        type=int,
        default=2,
        help="akumulasi gradien; efektif batch = batch-size x ini",
    )
    ap.add_argument("--lr", type=float, default=1e-5)
    ap.add_argument("--max-length", type=int, default=256)
    ap.add_argument("--val-ratio", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=5768)
    ap.add_argument("--device", default=None, help="cuda | cpu (default: auto)")
    ap.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    ap.add_argument("--metrics-path", default=str(DEFAULT_METRICS_PATH))
    ap.add_argument("--temperature-path", default=str(DEFAULT_TEMPERATURE_PATH))
    ap.add_argument("--train-path", default=None)
    ap.add_argument("--test-path", default=None)
    args = ap.parse_args(argv)

    train(
        base=args.base,
        epochs=args.epochs,
        batch_size=args.batch_size,
        grad_accum=args.grad_accum,
        lr=args.lr,
        max_length=args.max_length,
        val_ratio=args.val_ratio,
        seed=args.seed,
        device=args.device,
        output_dir=args.output_dir,
        metrics_path=args.metrics_path,
        temperature_path=args.temperature_path,
        train_path=args.train_path,
        test_path=args.test_path,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
