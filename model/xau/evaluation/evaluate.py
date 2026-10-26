"""Evaluasi artefak FinBERT-EMAS pada holdout test (M6).

Jalankan setelah training (kedua bentuk berikut setara):

    python -m model.xau.evaluation.evaluate
    python -m scripts.eval_xau_finbert        # pembungkus kompatibilitas

Menghasilkan laporan yang bisa ditempel apa adanya ke bab evaluasi:
macro-F1, per-kelas, confusion matrix, dan ECE sebelum/sesudah kalibrasi.

Kenapa dilaporkan terpisah dari training: bila evaluasi hanya dicetak di
dalam loop training, angka itu mudah "ikut berubah" saat training diulang.
Skrip ini membaca artefak beku, jadi hasilnya reprodusibel dan bisa diaudit
tanpa melatih ulang.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

from model.xau.src.data_loader import (
    LABEL_TO_TONE,
    get_texts_and_labels,
    load_gold_test,
)
from model.xau.src.model import (
    DEFAULT_CHECKPOINT_DIR,
    DEFAULT_TEMPERATURE_PATH,
    MAX_LENGTH,
)

#: Berkas ini sekarang tinggal di `model/xau/evaluation/`, jadi root repo
#: adalah tiga tingkat di atasnya (evaluation -> xau -> model -> root).
#: Sebelumnya `parents[1]` benar saat skrip masih di `scripts/`.
ROOT = Path(__file__).resolve().parents[3]
LABELS = [LABEL_TO_TONE[i] for i in range(3)]


def softmax_with_temperature(z: np.ndarray, t: float = 1.0) -> np.ndarray:
    """Softmax dengan suhu `t`. `t=1.0` = softmax biasa.

    Diangkat dari dalam `evaluate()` agar bisa diuji tanpa memuat model.
    `max(t, 1e-6)` mencegah pembagian nol bila suhu hasil kalibrasi rusak.
    """
    z = z / max(t, 1e-6)
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def build_report(
    y_true: np.ndarray,
    logits: np.ndarray,
    temperature: float,
    ece_pre: float,
    ece_post: float,
) -> dict[str, Any]:
    """Rakit laporan evaluasi dari prediksi & probabilitas yang sudah dihitung.

    Dipisah dari `evaluate()` (yang memuat model 440 MB) supaya seluruh
    perhitungan yang menghasilkan angka laporan dapat diuji tanpa GPU/jaringan.
    Sebelum pemisahan ini, `model/xau/evaluation/evaluate.py` 0% teruji
    (audit P1-5): angka macro-F1/ECE yang masuk bab evaluasi tidak diverifikasi
    oleh test apa pun.
    """
    from sklearn.metrics import classification_report, confusion_matrix, f1_score

    y_pred = logits.argmax(axis=1)
    macro_f1 = float(f1_score(y_true, y_pred, average="macro", zero_division=0))
    acc = float((y_pred == y_true).mean())

    report = classification_report(
        y_true, y_pred, labels=[0, 1, 2], target_names=LABELS, zero_division=0, output_dict=True
    )
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1, 2])

    return {
        "n_test": int(len(y_true)),
        "accuracy": round(acc, 6),
        "macro_f1": round(macro_f1, 6),
        "temperature": temperature,
        "ece_pre": round(ece_pre, 6),
        "ece_post": round(ece_post, 6),
        "ece_target": 0.1,
        "meets_target": bool(ece_post <= 0.1),
        "per_class": {
            tone: {
                "precision": round(float(report[tone]["precision"]), 6),
                "recall": round(float(report[tone]["recall"]), 6),
                "f1": round(float(report[tone]["f1-score"]), 6),
                "support": int(report[tone]["support"]),
            }
            for tone in LABELS
        },
        "confusion_matrix": {
            "labels": LABELS,
            "rows_true_cols_pred": cm.tolist(),
        },
    }


def evaluate(
    checkpoint_dir: Path = DEFAULT_CHECKPOINT_DIR,
    temperature_path: Path = DEFAULT_TEMPERATURE_PATH,
    batch_size: int = 32,
) -> dict[str, Any]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    from model.fomc.src.calibrator import TemperatureScaler, compute_multiclass_ece

    if not Path(checkpoint_dir).exists():
        raise SystemExit(
            f"Bobot tidak ada di {checkpoint_dir}.\n"
            "Latih dulu: python -m scripts.train_xau_finbert"
        )

    test_df = load_gold_test()
    texts, labels_int = get_texts_and_labels(test_df)
    y_true = np.asarray(labels_int, dtype=int)

    tok = AutoTokenizer.from_pretrained(str(checkpoint_dir))
    model = AutoModelForSequenceClassification.from_pretrained(
        str(checkpoint_dir), use_safetensors=True
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(device).eval()

    all_logits: list[np.ndarray] = []
    with torch.no_grad():
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            enc = tok(
                chunk, truncation=True, max_length=MAX_LENGTH, padding=True, return_tensors="pt"
            ).to(device)
            all_logits.append(model(**enc).logits.cpu().numpy())
    logits = np.vstack(all_logits)

    ece_pre = float(compute_multiclass_ece(softmax_with_temperature(logits), y_true))

    ece_post = ece_pre
    temp = 1.0
    probs_post = softmax_with_temperature(logits)
    if Path(temperature_path).exists():
        scaler = TemperatureScaler.load(temperature_path)
        temp = float(scaler.temperature)
        probs_post = scaler.predict_proba(logits)
        ece_post = float(compute_multiclass_ece(probs_post, y_true))

    return build_report(
        y_true=y_true,
        logits=logits,
        temperature=temp,
        ece_pre=ece_pre,
        ece_post=ece_post,
    )


def _print_summary(r: dict[str, Any]) -> None:
    print("=" * 62)
    print(f"Evaluasi holdout test  (n={r['n_test']})")
    print("=" * 62)
    print(f"  accuracy   : {r['accuracy']:.4f}")
    print(f"  macro-F1   : {r['macro_f1']:.4f}")
    print(f"  temperature: {r['temperature']:.4f}")
    print(f"  ECE        : {r['ece_pre']:.4f} -> {r['ece_post']:.4f}  "
          f"(target <= {r['ece_target']}, {'LULUS' if r['meets_target'] else 'BELUM'})")
    print()
    print(f"  {'kelas':<10}{'prec':>8}{'recall':>9}{'f1':>8}{'support':>9}")
    for k, v in r["per_class"].items():
        print(f"  {k:<10}{v['precision']:>8.3f}{v['recall']:>9.3f}{v['f1']:>8.3f}{v['support']:>9}")
    print()
    print("  Confusion matrix (baris=aktual, kolom=prediksi):")
    labels = r["confusion_matrix"]["labels"]
    print(f"  {'':>10}" + "".join(f"{c:>10}" for c in labels))
    for name, row in zip(labels, r["confusion_matrix"]["rows_true_cols_pred"]):
        print(f"  {name:>10}" + "".join(f"{int(x):>10}" for x in row))


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluasi FinBERT-EMAS pada holdout test")
    ap.add_argument("--checkpoint-dir", type=Path, default=DEFAULT_CHECKPOINT_DIR)
    ap.add_argument("--temperature", type=Path, default=DEFAULT_TEMPERATURE_PATH)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--json-out", type=Path, default=None)
    args = ap.parse_args()

    result = evaluate(args.checkpoint_dir, args.temperature, args.batch_size)
    _print_summary(result)

    out = args.json_out or (ROOT / "model/xau/evaluation/eval_report.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"\nLaporan JSON: {out}")


if __name__ == "__main__":
    main()
