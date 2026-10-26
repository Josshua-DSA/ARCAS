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
├── src/
│   ├── data_loader.py   # baca & bersihkan dataset/gold_sinha → text/label/date
│   └── model.py         # FinbertGoldSentiment (BaseSentimentModel)
├── notebooks/           # eksplorasi & verifikasi (bukan jalur produksi)
├── weights/             # artefak beku; bobot TIDAK di-commit
└── evaluation/          # laporan evaluasi hold-out
```

## Cara pakai

```bash
# 1. latih + kalibrasi + tulis metrics.json & temperature.json
python -m scripts.train_xau_finbert --epochs 3 --batch-size 16

# 2. evaluasi artefak beku pada holdout test
python -m scripts.eval_xau_finbert
```

Inferensi:

```python
from model.xau.src.model import FinbertGoldSentiment

m = FinbertGoldSentiment()
probs = m.predict_probs(["gold prices surge on safe-haven demand"])
artikel = m.score_article("art-1", "gold prices surge on safe-haven demand")
```

## Sumber data (jujur, bukan sesuai nama folder)

`dataset/gold_sinha/` berasal dari **Sinha & Khandait 2020** (`arXiv:2009.04202`),
tetapi berkas yang ada di repo ini adalah **re-upload pihak ketiga**
(`SaguaroCapital/...` dalam format HuggingFace Hub), bukan salinan dari penulis.
Isinya terverifikasi identik dengan dataset Kaggle penulis (10.570 baris).

Hasil verifikasi lapangan yang menyimpang dari README sumber:

| Klaim README sumber | Kenyataan |
|---|---|
| rentang 2000–2021 | **2000-02-15 s.d. 2019-02-01**, 127 tanggal tak terbaca |
| — | 3.531 positive / 3.050 negative / 1.574 **none** / 301 neutral |

Lisensi **CC BY-NC-ND 4.0**: boleh untuk riset non-komersial; dataset tidak
boleh didistribusikan ulang dalam bentuk turunan. Model hasil latih bukan
"derivative work" dataset menurut praktik umum, tetapi **jangan commit data
mentah yang dimodifikasi**.

## Artefak: tidak di-commit

Bobot (~440 MB) **sengaja tidak masuk git** — mengikuti pola repo untuk
artefak sklearn (`.joblib` juga tidak di-commit karena terikat versi library).
`weights/` hanya menyimpan metadata kecil:

- `metrics.json` — metrik val/test, hyperparameter, versi model
- `temperature.json` — suhu kalibrasi + ECE sebelum/sesudah
- `finbert_gold/` — bobot + tokenizer (dibuat oleh skrip latih, di-*gitignore*)

Reprodusibel karena seed dipatok (`5768`) dan dataset ikut ter-commit.

## Catatan teknis yang mudah salah

1. **Urutan probabilitas.** Label latih `0=neg, 1=neu, 2=pos`, sedangkan
   protokol mewajibkan `[p_pos, p_neu, p_neg]`. Konversi dilakukan lewat
   `_PROTOCOL_ORDER = (2, 1, 0)`; bila salah, model melaporkan sentimen
   terbalik **tanpa error apa pun**.
2. **`none` dibuang, bukan jadi neutral.** "Tidak membahas harga" berbeda
   dengan "harga stabil"; menggabungkannya mengajari model hal yang salah.
3. **Macro-F1 sebagai metrik utama**, bukan accuracy — `neutral` hanya ~4%.

## Keterbatasan

- Rentang latih berakhir 2019: tidak mencakup rezim 2020–2026.
- Dominan media India + AS; kosakata emas Indonesia (`Antam`, `logam mulia`)
  tidak dikenal. Untuk teks ID hanya boleh via terjemahan, dan
  `translation_used=True` wajib dicatat.
- Dirancang untuk **headline**, bukan paragraf penuh.

## Catatan lingkungan (penting sebelum menjalankan training)

Lingkungan dev saat ini: **Python 3.12.3**, `torch 2.5.1+cu121`, `transformers 4.57.6`,
GPU RTX 3050 6 GB, driver 595.99.

1. **Jangan pasang `transformers>=5`.** v5 menuntut `torch>=2.6`; wheel cu121
   berhenti di 2.5.1. Kalau terlanjur, `pip install "transformers>=4.30,<5"`.
2. **`use_safetensors=True` wajib** saat memuat bobot. transformers ≥4.56
   menolak `torch.load` pada torch <2.6 (CVE-2025-32434). Checkpoint
   `yiyanghkust/finbert-tone` menyediakan safetensors sehingga jalur ini aman
   dan **tidak perlu** menaikkan torch. Sudah diterapkan di
   `scripts/train_xau_finbert.py`, `scripts/eval_xau_finbert.py`, dan
   `model/xau/src/model.py`.
3. **`pip` tanpa batas waktu bisa gagal di tengah.** Unduhan torch ~2,5 GB;
   jika `ReadTimeoutError`, ulangi dengan `--timeout 120 --retries 15`
   (wheel tersimpan di cache pip sehingga lanjut, bukan mulai dari nol).
4. **mypy perlu `--python-version 3.12`.** `pyproject.toml` menargetkan 3.11,
   tetapi numpy 2.5 di venv memakai sintaks `type` yang hanya dikenal 3.12;
   tanpa flag ini mypy berhenti dengan error `syntax` yang menyesatkan.
5. **Setelah torch terpasang, suite test jadi lebih lambat** karena test
   integrasi FOMC yang tadinya di-skip kini benar-benar mengunduh
   `FOMC-RoBERTa`. Itu di luar cakupan track ini.

## Kontrak

Semua model di track ini wajib mengimplementasikan
`model.common.protocol.BaseSentimentModel` (`predict_probs`, `score_article`)
agar bisa dipakai langsung oleh `backend/src/tagging/router.py`.
