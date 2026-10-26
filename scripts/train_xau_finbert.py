"""Latih FinBERT-EMAS pada korpus gold Sinha (FR-6 / M2 + M6).

Jalankan dari akar repo:

    python -m scripts.train_xau_finbert                      # default
    python -m scripts.train_xau_finbert --epochs 3 --batch-size 16

Alur:
  1. muat & bersihkan korpus (`model/xau/src/data_loader.py`),
  2. split train/val stratified dari split train (test TIDAK disentuh),
  3. fine-tune FinBERT penuh (semua bobot),
  4. pilih checkpoint terbaik menurut macro-F1 validation,
  5. kalibrasi temperature pada validation (M6),
  6. tulis bobot + `metrics.json` + `temperature.json` ke `model/xau/weights/`.

Kenapa macro-F1, bukan accuracy: kelas `neutral` hanya ~4% korpus. Accuracy
akan tampak ~77% hanya dengan menebak positive/negative, sementara model yang
mengabaikan neutral sepenuhnya tetap terlihat bagus. Macro-F1 memberi bobot
sama ke tiap kelas sehingga kelemahan itu terlihat.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from model.xau.src.data_loader import (
    LABEL_TO_TONE,
    get_texts_and_labels,
    load_gold_test,
    load_gold_train,
    split_train_val,
)
from model.xau.src.model import (
    BASE_CHECKPOINT,
    DEFAULT_CHECKPOINT_DIR,
    DEFAULT_METRICS_PATH,
    DEFAULT_TEMPERATURE_PATH,
    MAX_LENGTH,
)

ROOT = Path(__file__).resolve().parents[1]
LABELS = [LABEL_TO_TONE[i] for i in range(3)]  # ["negative", "neutral", "positive"]


def _macro_f1(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    from sklearn.metrics import f1_score

    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))


def _class_report(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    """Presisi/recall/F1 per kelas — tanpa ini, rata-rata menyembunyikan neutral."""
    from sklearn.metrics import precision_recall_fscore_support

    prec, rec, f1, sup = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1, 2], zero_division=0  # type: ignore[arg-type]
    )
    report: dict[str, Any] = {}
    for i, tone in enumerate(LABELS):
        report[tone] = {
            "precision": float(prec[i]),
            "recall": float(rec[i]),
            "f1": float(f1[i]),
            "support": int(sup[i]),
        }
    return report


def train(
    epochs: int = 3,
    batch_size: int = 16,
    lr: float = 2e-5,
    val_fraction: float = 0.15,
    seed: int = 5768,
    checkpoint: str = BASE_CHECKPOINT,
    out_dir: Path = DEFAULT_CHECKPOINT_DIR,
    max_length: int = MAX_LENGTH,
) -> dict[str, Any]:
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )

    torch.manual_seed(seed)
    np.random.seed(seed)

    train_full = load_gold_train()
    test_df = load_gold_test()
    train_df, val_df = split_train_val(train_full, val_fraction=val_fraction, seed=seed)

    print(f"train={len(train_df)}  val={len(val_df)}  test={len(test_df)}")
    print("distribusi train:", train_df["tone"].value_counts().to_dict())

    tokenizer = AutoTokenizer.from_pretrained(checkpoint)
    # `use_safetensors=True` WAJIB: transformers >=4.56 menolak torch.load di
    # torch <2.6 (CVE-2025-32434). Checkpoint finbert-tone menyediakan
    # safetensors, jadi jalur aman ini tersedia dan tidak perlu menaikkan torch.
    model = AutoModelForSequenceClassification.from_pretrained(
        checkpoint, num_labels=3, use_safetensors=True
    )

    class _DS(Dataset):  # type: ignore[misc]
        def __init__(self, texts: list[str], labels: list[int]) -> None:
            self.enc = tokenizer(
                texts,
                truncation=True,
                max_length=max_length,
                padding="max_length",
                return_tensors="pt",
            )
            self.labels = torch.tensor(labels, dtype=torch.long)

        def __len__(self) -> int:
            return len(self.labels)

        def __getitem__(self, i: int) -> dict[str, Any]:
            return {
                "input_ids": self.enc["input_ids"][i],
                "attention_mask": self.enc["attention_mask"][i],
                "labels": self.labels[i],
            }

    xtr, ytr = get_texts_and_labels(train_df)
    xva, yva = get_texts_and_labels(val_df)
    dl_tr = DataLoader(_DS(xtr, ytr), batch_size=batch_size, shuffle=True)
    dl_va = DataLoader(_DS(xva, yva), batch_size=batch_size * 2)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"device={device}")
    model.to(device)

    optim = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    total_steps = max(1, len(dl_tr) * epochs)
    sched = get_linear_schedule_with_warmup(
        optim, num_warmup_steps=int(0.1 * total_steps), num_training_steps=total_steps
    )
    scaler = torch.amp.GradScaler("cuda", enabled=(device == "cuda"))

    best_f1 = -1.0
    best_state: dict[str, Any] | None = None
    history: list[dict[str, Any]] = []

    for ep in range(1, epochs + 1):
        model.train()
        running = 0.0
        for step, batch in enumerate(dl_tr, start=1):
            batch = {k: v.to(device) for k, v in batch.items()}
            optim.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=(device == "cuda")):
                loss = model(**batch).loss
            scaler.scale(loss).backward()
            scaler.unscale_(optim)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optim)
            scaler.update()
            sched.step()
            running += float(loss.item())
            if step % 50 == 0:
                print(f"  ep{ep} step {step}/{len(dl_tr)} loss={running/step:.4f}")

        # --- validasi ---
        model.eval()
        preds: list[int] = []
        with torch.no_grad():
            for batch in dl_va:
                batch = {k: v.to(device) for k, v in batch.items()}
                logits = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
                preds.extend(logits.argmax(dim=-1).cpu().tolist())
        y_pred = np.array(preds)
        y_true = np.array(yva)
        f1 = _macro_f1(y_true, y_pred)
        acc = float((y_pred == y_true).mean())
        history.append({"epoch": ep, "train_loss": running / max(1, len(dl_tr)), "val_macro_f1": f1, "val_accuracy": acc})
        print(f"epoch {ep}: loss={running/max(1,len(dl_tr)):.4f} val_macroF1={f1:.4f} val_acc={acc:.4f}")

        if f1 > best_f1:
            best_f1 = f1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            print(f"  -> checkpoint terbaik (macro-F1={f1:.4f})")

    if best_state is not None:
        model.load_state_dict(best_state)

    # --- simpan bobot ---
    out_dir.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    print(f"bobot disimpan ke {out_dir}")

    # --- kalibrasi temperature pada validation ---
    model.eval()
    val_logits: list[np.ndarray] = []
    with torch.no_grad():
        for batch in dl_va:
            batch = {k: v.to(device) for k, v in batch.items()}
            lg = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
            val_logits.append(lg.cpu().numpy())
    logits_arr = np.vstack(val_logits)

    from model.fomc.src.calibrator import TemperatureScaler

    # `fit()` sudah menghitung ece_pre/ece_post sendiri; jangan hitung ulang
    # dengan urutan argumen yang mudah terbalik (probs dulu, baru labels).
    scaler_t = TemperatureScaler()
    scaler_t.fit(logits_arr, list(map(int, np.asarray(yva, dtype=int))))
    ece_pre = float(scaler_t.ece_pre or 0.0)
    ece_post = float(scaler_t.ece_post or 0.0)
    print(f"temperature={scaler_t.temperature:.4f}  ECE {ece_pre:.4f} -> {ece_post:.4f}")

    temperature_path = Path(DEFAULT_TEMPERATURE_PATH)
    temperature_path.parent.mkdir(parents=True, exist_ok=True)
    temperature_path.write_text(
        json.dumps(
            {
                "model": "finbert_gold",
                "temperature": round(float(scaler_t.temperature), 6),
                "ece_pre": round(float(ece_pre), 6),
                "ece_post": round(float(ece_post), 6),
                "ece_target": 0.1,
                "meets_target": bool(ece_post <= 0.1),
                "n_samples": int(len(yva)),
                "fitted_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    # --- evaluasi akhir pada TEST (holdout, sekali saja) ---
    xts, yts = get_texts_and_labels(test_df)
    dl_ts = DataLoader(_DS(xts, yts), batch_size=batch_size * 2)
    test_preds: list[int] = []
    test_logits: list[np.ndarray] = []
    with torch.no_grad():
        for batch in dl_ts:
            batch = {k: v.to(device) for k, v in batch.items()}
            lg = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
            test_logits.append(lg.cpu().numpy())
            test_preds.extend(lg.argmax(dim=-1).cpu().tolist())
    y_test = np.array(yts)
    y_test_pred = np.array(test_preds)
    test_f1 = _macro_f1(y_test, y_test_pred)
    test_acc = float((y_test_pred == y_test).mean())
    print(f"TEST: macro-F1={test_f1:.4f}  acc={test_acc:.4f}")

    metrics = {
        "model": "finbert_gold",
        "model_version": f"xau-finbert-{datetime.now(timezone.utc).strftime('%Y%m%d')}",
        "base_checkpoint": checkpoint,
        "max_length": max_length,
        "seed": seed,
        "epochs": epochs,
        "batch_size": batch_size,
        "lr": lr,
        "val_fraction": val_fraction,
        "n_train": int(len(train_df)),
        "n_val": int(len(val_df)),
        "n_test": int(len(test_df)),
        "label_order": LABELS,
        "best_val_macro_f1": round(float(best_f1), 6),
        "test_macro_f1": round(test_f1, 6),
        "test_accuracy": round(test_acc, 6),
        "test_per_class": _class_report(y_test, y_test_pred),
        "history": history,
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    metrics_path = Path(DEFAULT_METRICS_PATH)
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"metrik disimpan ke {metrics_path}")
    return metrics


def main() -> None:
    ap = argparse.ArgumentParser(description="Latih FinBERT-EMAS pada korpus gold Sinha")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--val-fraction", type=float, default=0.15)
    ap.add_argument("--seed", type=int, default=5768)
    ap.add_argument("--checkpoint", default=BASE_CHECKPOINT)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    args = ap.parse_args()
    train(
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        val_fraction=args.val_fraction,
        seed=args.seed,
        checkpoint=args.checkpoint,
        out_dir=args.out_dir,
    )


if __name__ == "__main__":
    main()
