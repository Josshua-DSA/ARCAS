# xau/ — Track FinBERT-EMAS (target XAU)

Model sentimen khusus berita emas. Sumber data: `dataset/gold_sinha/`
(8.456 train / 2.114 test, rentang 2000–2019).

## Tugas track ini (M2, M6)

- Fine-tune FinBERT pada korpus gold, mapping label
  `Positive → 2`, `Neutral → 1`, `Negative → 0`.
- Baris berlabel `Price Sentiment: none` **dibuang**, tidak digabung ke neutral
  (lihat `backend/src/normalize/adapters.py:gold_tone`).
- Kalibrasi probabilitas (M6) dan ekspor metadata metrik ke `weights/`.

## Kerangka

```
xau/
├── src/          # loader + inferensi (implementasi BaseSentimentModel)
├── notebooks/    # fine-tune & validasi temporal
├── weights/      # artefak beku: *.pkl, *.safetensors, *.onnx, calibrator
└── evaluation/   # evaluasi pada hold-out dataset/gold_sinha/test
```

## Yang belum ada

`model/xau/src/` masih kosong — belum ada implementasi FinBERT. Yang tersedia
baru baseline TF-IDF generik di `model/common/baseline.py`, dan router
mengembalikan id `finbert_emas` tanpa kelas yang menanganinya.

## Kontrak

Semua model di track ini wajib mengimplementasikan
`model.common.protocol.BaseSentimentModel` (`predict_probs`, `score_article`)
agar bisa dipakai langsung oleh `backend/src/tagging/router.py`.
