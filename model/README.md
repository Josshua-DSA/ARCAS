# model/ — ML Research & Inference Pipeline (M1–M7)

Lingkup kerja ML Engineer:
- `notebooks/`: EDA, eksperimen training, validasi temporal (strict non-destructive).
- `weights/`: Artefak model beku (`.pkl`, safetensors, tokenizer, kalibrator ECE).
- `evaluation/`: Skrip metrik (F1 macro, ECE, Brier, McNemar, bootstrap CI).

## Pemetaan Modul (M1–M7)
- **M1**: Baseline TF-IDF + Logistic Regression (F1 macro).
- **M2**: Fine-tune FinBERT (gold `XAU`, mapping Up/Down/Constant).
- **M3**: Fine-tune/eval FOMC-RoBERTa (FOMC `RATE_UST`+`SPX`, mapping LABEL_1/0/2).
- **M4**: ~~MT ID→EN~~ — MATI 2026-10-11 (Track A hapus).
- **M5**: ~~Late Fusion~~ — MATI 2026-10-11 (satu track EN; ablation langsung TF-IDF vs transformer).
- **M6**: Kalibrasi probabilitas ECE (Temperature Scaling / Isotonic).
- **M7**: Klasifier tema makro multi-label (7 tema `impact_graph.yaml`).

Kontrak luaran ke `backend/`: inferensi probabilistik (`p_pos, p_neu, p_neg`), kelas argmax, skor kalibrasi.
