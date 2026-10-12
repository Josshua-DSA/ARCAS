# Model Research Notebooks

Direktori khusus eksperimen, eksplorasi data, dan pelatihan model offline.
Sesuai konvensi proyek, seluruh notebook riset disimpan di sini dan terpisah tegas dari pipeline eksekusi produksi (`backend/` dan UI yang mengonsumsi artefak terserialisasi).

## Struktur Notebook:
- `01_baseline_exploration.py`: Baseline TF-IDF + Logistic Regression per dataset (gold + FOMC).
- `02_finbert_gold.py`: Fine-tune FinBERT gold `XAU` (ganti `02_indobert_finetuning.py` yang mati 2026-10-11).
- `03_fomc_roberta.py`: Eval/fine-tune FOMC-RoBERTa `RATE_UST`+`SPX` (ganti `03_finbert_mt_pipeline.py` yang mati 2026-10-11).

## Standar Output Artefak:
Model yang telah dilatih dan dievaluasi diekspor ke format `.pkl` atau direktori bobot model dengan metadata metrik (F1 macro, ECE, Cohen's kappa) sebelum dikonsumsi oleh runtime inferensi.
