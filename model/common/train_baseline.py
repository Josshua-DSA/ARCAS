"""Melatih baseline TF-IDF + LR dari dataset gold_sinha (nyata, berlabel).

Dataset: `dataset/gold_sinha/data/*.parquet` — Sinha & Khandait 2020,
kolom `News` (teks) dan `Price Sentiment` (positive/negative/neutral/none).

Pemetaan label ke 3 kelas:
    positive -> 2 · neutral -> 1 · negative -> 0 · none -> dibuang

`none` dibuang karena berarti "tidak ada berita relevan", bukan sentimen netral.
Mencampurnya ke kelas netral akan mengajari model bahwa kalimat kosong itu netral.

Pemakaian:
    python -m model.common.train_baseline
    python -m model.common.train_baseline --out model/common/baseline_tfidf.joblib
"""

from __future__ import annotations

import argparse
from pathlib import Path

from model.common.baseline import LABEL_TO_INT, BaselineTfidfSentiment

DEFAULT_TRAIN = Path("dataset/gold_sinha/data/train-00000-of-00001.parquet")
DEFAULT_TEST = Path("dataset/gold_sinha/data/test-00000-of-00001.parquet")
DEFAULT_OUT = Path("model/common/baseline_tfidf.joblib")

# Batas minimum akurasi test agar training yang buruk tidak lolos diam-diam.
MIN_ACCEPTABLE_ACCURACY = 0.60


def load_split(path: Path) -> tuple[list[str], list[int]]:
    """Membaca satu split parquet, mengembalikan (texts, labels)."""
    import pandas as pd

    if not path.exists():
        raise FileNotFoundError(f"Dataset tidak ditemukan: {path}")

    df = pd.read_parquet(path)
    df = df[df["Price Sentiment"].isin(LABEL_TO_INT)].copy()
    df["News"] = df["News"].fillna("").astype(str).str.strip()
    df = df[df["News"].str.len() > 0]

    texts = df["News"].tolist()
    labels = [LABEL_TO_INT[s] for s in df["Price Sentiment"]]
    return texts, labels


def train(
    train_path: Path = DEFAULT_TRAIN,
    test_path: Path = DEFAULT_TEST,
    out_path: Path = DEFAULT_OUT,
) -> dict:
    """Melatih dan menyimpan model. Mengembalikan metrik evaluasi."""
    from sklearn.metrics import accuracy_score, f1_score

    x_train, y_train = load_split(train_path)
    if not x_train:
        raise ValueError(f"Data latih kosong setelah filter: {train_path}")

    model = BaselineTfidfSentiment().fit(x_train, y_train)

    metrics: dict = {"n_train": len(x_train)}
    if test_path.exists():
        x_test, y_test = load_split(test_path)
        if x_test:
            preds = [max(range(3), key=lambda i: p[i]) for p in _proba_matrix(model, x_test)]
            metrics |= {
                "n_test": len(x_test),
                "accuracy": round(float(accuracy_score(y_test, preds)), 4),
                "f1_macro": round(float(f1_score(y_test, preds, average="macro")), 4),
            }
            if metrics["accuracy"] < MIN_ACCEPTABLE_ACCURACY:
                raise RuntimeError(
                    f"Akurasi test {metrics['accuracy']:.2%} di bawah batas "
                    f"{MIN_ACCEPTABLE_ACCURACY:.0%}. Model tidak disimpan."
                )

    saved = model.save(out_path)
    metrics["saved_to"] = str(saved)
    return metrics


def _proba_matrix(model: BaselineTfidfSentiment, texts: list[str]) -> list[list[float]]:
    probs = model.predict_probs(texts)
    return [[p.p_neg, p.p_neu, p.p_pos] for p in probs]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="train_baseline",
        description="Latih baseline TF-IDF + LR dari dataset gold_sinha.",
    )
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--test", type=Path, default=DEFAULT_TEST)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    metrics = train(args.train, args.test, args.out)
    for key, value in metrics.items():
        print(f"{key:<12} {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
