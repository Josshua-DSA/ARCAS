# model/ — ML Research & Inference Pipeline (M1–M7)

Direktori ini dibagi **per domain korpus**, bukan lagi per jenis artefak.
Setiap track punya kerangka yang sama: `src/`, `notebooks/`, `weights/`,
`evaluation/`.

```
model/
├── common/          # dipakai kedua track — jangan diduplikasi
│   ├── protocol.py      # BaseSentimentModel (kontrak inferensi)
│   ├── baseline.py      # M1 TF-IDF + Logistic Regression (algoritma)
│   ├── metrics.py       # F1 macro, ECE, Cohen's kappa
│   ├── router_centroids.json  # bobot router lintas-korpus (gold vs FOMC)
│   └── 01_baseline_exploration.py
│
├── xau/             # FinBERT-EMAS — target XAU (gold)
│   ├── src/         # loader & inferensi FinBERT
│   ├── notebooks/   # fine-tune, validasi temporal
│   ├── weights/     # artefak beku (.pkl / safetensors / onnx)
│   └── evaluation/  # evaluasi pada dataset/gold_sinha
│
└── fomc/            # FOMC-RoBERTa — target RATE_UST + SPX
    ├── src/
    ├── notebooks/
    ├── weights/
    └── evaluation/
```

## Aturan pembagian

- **Domain-spesifik** (loader model, notebook training, bobot, evaluasi) →
  `xau/` atau `fomc/`.
- **Dipakai bersama** (kontrak, metrik, algoritma, bobot router) → `common/`.
  Jangan menyalin `protocol.py` atau `metrics.py` ke dalam track domain: dua
  salinan akan bercabang dan membuat `backend/` ambigu soal mana yang dipakai.

## Pemetaan Modul (M1–M7)

- **M1**: Baseline TF-IDF + Logistic Regression → `common/baseline.py`.
- **M2**: Fine-tune FinBERT (gold `XAU`, mapping Up/Down/Constant) → `xau/`.
- **M3**: Fine-tune/eval FOMC-RoBERTa (FOMC `RATE_UST`+`SPX`, LABEL_1/0/2) → `fomc/`.
- **M4**: ~~MT ID→EN~~ — MATI 2026-10-11 (Track A hapus).
- **M5**: ~~Late Fusion~~ — MATI 2026-10-11 (satu track EN; ablation langsung TF-IDF vs transformer).
- **M6**: Kalibrasi probabilitas ECE (Temperature Scaling / Isotonic) — per track.
- **M7**: Klasifier tema makro multi-label (7 tema `impact_graph.yaml`) — per track.

Kontrak luaran ke `backend/`: inferensi probabilistik (`p_pos, p_neu, p_neg`),
kelas argmax, skor kalibrasi.
