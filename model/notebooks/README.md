# Model Research Notebooks

Direktori khusus eksperimen, eksplorasi data, dan pelatihan model offline.
Sesuai konvensi proyek, seluruh notebook riset disimpan di sini dan terpisah tegas dari pipeline eksekusi produksi (`backend/` dan UI yang mengonsumsi artefak terserialisasi).

## Struktur Notebook:
- `01_baseline_exploration.py`: Skrip eksplorasi dan evaluasi baseline TF-IDF + Logistic Regression pada Track A (Indo) & Track B (EN).
- `02_indobert_finetuning.py`: Template fine-tuning IndoBERT (Track A).
- `03_finbert_mt_pipeline.py`: Pipeline translasi mesin + FinBERT (Track B & fused).

## Standar Output Artefak:
Model yang telah dilatih dan dievaluasi diekspor ke format `.pkl` atau direktori bobot model dengan metadata metrik (F1 macro, ECE, Cohen's kappa) sebelum dikonsumsi oleh runtime inferensi.
