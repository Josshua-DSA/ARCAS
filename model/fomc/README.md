# fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX)

Model stance hawkish/dovish dari pernyataan FOMC, dipetakan ke dua target.
Sumber data: `dataset/fomc/` — varian terkunci
`lab-manual-split-combine-train-5768.xlsx` (seed 5768) saja.

## Tugas track ini (M3, M6)

- Fine-tune / evaluasi FOMC-RoBERTa, mapping `LABEL_1/0/2` → stance.
- Stance dipetakan ke tone per aset lewat `fomc_tone(stance, asset_id)`
  di `backend/src/normalize/adapters.py` — satu stance menghasilkan tone
  berbeda untuk `RATE_UST` dan `SPX`.
- Kalibrasi probabilitas (M6) dan ekspor metadata metrik ke `weights/`.

## Kerangka

```
fomc/
├── src/          # loader + inferensi (implementasi BaseSentimentModel)
├── notebooks/    # fine-tune & evaluasi
├── weights/      # artefak beku: *.pkl, *.safetensors, *.onnx, calibrator
└── evaluation/   # evaluasi pada split test 5768
```

## Yang belum ada

`model/fomc/src/` masih kosong — belum ada implementasi FOMC-RoBERTa. Router
mengembalikan id `fomc_roberta` tanpa kelas yang menanganinya.

## Kontrak

Semua model di track ini wajib mengimplementasikan
`model.common.protocol.BaseSentimentModel` agar bisa dipakai langsung oleh
`backend/src/tagging/router.py`.
