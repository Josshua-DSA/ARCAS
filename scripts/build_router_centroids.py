"""Build domain log-odds z-scores for the cascade router stage 2.

Metode: log-odds ratio berprior Dirichlet informatif (Monroe, Colaresi & Quinn
2008, "Fightin' Words"). Dipakai karena membandingkan dua korpus dan meredam
artefak kata langka — tanpa prior, kata yang tidak pernah muncul di satu korpus
otomatis condong ke korpus lain.

Output: model/weights/router_centroids.json
Skor dokumen = rata-rata z token yang dikenal. z > 0 condong gold, z < 0 FOMC.

Jalankan ulang bila dataset benchmark berubah, lalu naikkan `version` di
data/router_config.yaml agar routing tetap dapat diaudit.
"""

import json
import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.src.tagging.model_router import tokens  # noqa: E402  sumber tokenizer tunggal

ROOT = Path(__file__).resolve().parents[1]
GOLD_PARQUET = ROOT / "dataset/gold_sinha/data/train-00000-of-00001.parquet"
FOMC_XLSX = ROOT / "dataset/fomc/train/lab-manual-split-combine-train-5768.xlsx"
OUT = ROOT / "model/weights/router_centroids.json"

VERSION = "2026-10-19-r4"
PRIOR = 5000.0  # alpha_0, ukuran prior; lebih besar = lebih konservatif
MIN_COUNT = 5   # buang token yang terlalu jarang untuk dipercaya


def load_docs() -> dict[str, list[str]]:
    gold = pd.read_parquet(GOLD_PARQUET)["News"].dropna()
    fomc = pd.read_excel(FOMC_XLSX)["sentence"].dropna()
    return {
        "finbert_emas": [str(x) for x in gold],
        "fomc_roberta": [str(x) for x in fomc],
    }


def counts(corpus: list[str]) -> tuple[dict[str, int], int]:
    c: dict[str, int] = {}
    total = 0
    for doc in corpus:
        for t in tokens(doc):
            c[t] = c.get(t, 0) + 1
            total += 1
    return c, total


def build(docs: dict[str, list[str]]) -> dict:
    ca, na = counts(docs["finbert_emas"])
    cb, nb = counts(docs["fomc_roberta"])
    if not na or not nb:
        raise SystemExit("korpus kosong")
    n_total = na + nb

    z: dict[str, float] = {}
    for t in set(ca) | set(cb):
        ya, yb = ca.get(t, 0), cb.get(t, 0)
        if ya + yb < MIN_COUNT:
            continue
        # prior informatif: porsi token dialokasikan sebanding frekuensi gabungan
        alpha = PRIOR * (ya + yb) / n_total
        la = math.log((ya + alpha) / (na + PRIOR - ya - alpha))
        lb = math.log((yb + alpha) / (nb + PRIOR - yb - alpha))
        var = 1.0 / (ya + alpha) + 1.0 / (yb + alpha)
        z[t] = (la - lb) / math.sqrt(var)

    return {
        "version": VERSION,
        "method": "log_odds_dirichlet_prior",
        "prior": PRIOR,
        "min_count": MIN_COUNT,
        "n_docs": {k: len(v) for k, v in docs.items()},
        "n_tokens": {"finbert_emas": na, "fomc_roberta": nb},
        "weights": z,
    }


def main() -> int:
    docs = load_docs()
    if not all(docs.values()):
        print("dataset kosong", file=sys.stderr)
        return 1
    payload = build(docs)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload), encoding="utf-8")
    print(f"{OUT} version={payload['version']} docs={payload['n_docs']} vocab={len(payload['weights'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
