# model/ — ML Research & Inference Pipeline (M1–M7)

Lingkup kerja ML Engineer:
- `notebooks/`: EDA, eksperimen training, validasi temporal (strict non-destructive).
- `weights/`: Artefak model beku (`.pkl`, safetensors, tokenizer, kalibrator ECE).
- `evaluation/`: Skrip metrik (F1 macro, ECE, Brier, McNemar, bootstrap CI).

## Pemetaan Modul (M1–M7)
- **M1**: Baseline TF-IDF + Logistic Regression (F1 macro).
- **M2**: Fine-tune IndoBERT (korpus berita finansial ID).
- **M3**: Fine-tune FinBERT (korpus berita finansial EN).
- **M4**: Pipeline MT (Machine Translation ID→EN) untuk uji ablasi transfer.
- **M5**: Late Fusion (Stacking OOF vs Weighted Average).
- **M6**: Kalibrasi probabilitas ECE (Temperature Scaling / Isotonic).
- **M7**: Klasifier tema makro multi-label (7 tema `impact_graph.yaml`).

Kontrak luaran ke `backend/`: inferensi probabilistik (`p_pos, p_neu, p_neg`), kelas argmax, skor kalibrasi.
