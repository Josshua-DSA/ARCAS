# Model Router: Cascade Routing ke Model Spesialis

Dokumen ini menjelaskan keputusan routing berita ke model spesialis (`finbert_emas`,
`fomc_roberta`) dan alasan di balik setiap parameter. Tanpa catatan ini, angka ambang
di `data/router_config.yaml` tidak dapat dipertanggungjawabkan saat audit.

## Masalah

Dua model dilatih pada distribusi teks yang berbeda dan sempit:

| Model | Data latih | Domain |
|---|---|---|
| `finbert_emas` | Sinha gold news (8.456 baris) | komoditas emas |
| `fomc_roberta` | FOMC transcripts (1.984 baris) | kebijakan moneter |

Berita harian masuk dalam bentuk acak. Berita emas tidak boleh masuk RoBERTa, dan
risalah Fed tidak boleh masuk FinBERT. Karena itu perlu pemilah sebelum inferensi.

## Arsitektur: dua tahap + fallback

```
Berita (teks, source)
        │
        ▼
[Tahap 1] petunjuk sumber → kamus kata kunci
        │  cocok  → model spesialis (reason=source|keyword)
        ▼ tidak cocok
[Tahap 2] bukti log-odds per token
        │  cukup bukti → model spesialis (reason=log_odds)
        ▼ tidak cukup
[Fallback] baseline_tfidf
```

Alasan urutan ini: tahap 1 menangani mayoritas kasus secara deterministik dan murah,
tahap 2 hanya menyentuh sisa kasus yang istilahnya implisit atau bersinonim.

## Tahap 1 — sumber dan kata kunci

- Petunjuk sumber (Kitco, WGC, federalreserve.gov) langsung memutuskan, karena
  asal terbitan adalah bukti paling kuat.
- Kamus kata kunci dicocokkan sebagai kata utuh dengan toleransi bentuk jamak
  sederhana (`rate cut` cocok dengan `rate cuts`).
- Bila satu teks memuat kata kunci kedua domain ("Gold hits record as Fed pauses"),
  keduanya dikembalikan — berita makro memang dapat memengaruhi dua target.
- Kata kunci Indonesia (`emas`, `logam mulia`) disertakan karena kolektor akan
  menyedot media lokal.

## Tahap 2 — bukti log-odds

Bobot dibangun oleh `scripts/build_router_centroids.py` dengan metode **log-odds ratio
berprior Dirichlet informatif** (Monroe, Colaresi & Quinn 2008, *Fightin' Words*).
Prior dipakai karena membandingkan dua korpus: tanpa prior, kata yang tidak pernah
muncul di satu korpus otomatis dianggap bukti sempurna.

Rumus per token `t`:

```
alpha = prior * (y_gold + y_fomc) / n_total
z(t)  = (log_odds_gold - log_odds_fomc) / sqrt(var)
```

Parameter yang dipilih, beserta hasil ukurnya pada 400 sampel acak per korpus
(`random.seed(0)`):

| Parameter | Nilai | Akurasi gold | Akurasi FOMC | Salah rute |
|---|---|---|---|---|
| `z_min=3.0`, `min_votes=2` | dipakai | 94.8% | 97.8% | ≤0.75% |
| `z_min=2.5`, `min_votes=2` | lebih longgar | 94.8% | 98.8% | ≤0.75% |
| `z_min=3.0`, `min_votes=3` | lebih ketat | 88.5% | 96.8% | ≤0.50% |

### Mengapa aturan bukti, bukan rata-rata

Versi awal memakai rata-rata z seluruh token. Itu gagal: "Local weather forecast for
Jakarta" dirutekan ke `fomc_roberta` karena satu kata `forecast` ber-|z|=6 menyeret
rata-rata melewati ambang. Rata-rata buta memberi bobot sama pada satu kata kuat dan
lima kata netral.

Aturan sekarang menuntut minimal `min_votes` token dengan `|z| >= z_min` yang searah.
Teks di luar domain tidak punya dua token semacam itu, sehingga jatuh ke fallback —
perilaku yang benar, bukan salah rute yang senyap.

`min_votes=3` ditolak karena memotong akurasi gold ke 88.5%: kalimat berita emas sering
pendek dan hanya memuat dua istilah khas.

## Jejak audit

Keputusan routing tidak boleh hilang. Karena itu:

- `TargetImpact.routed_from` menyimpan `reason:model`, mis. `log_odds:fomc_roberta`.
- `TargetImpact.route_score` menyimpan skor yang mendasari keputusan.
- Keduanya dipersist ke tabel `impacts` (`routed_from`, `route_score`) dan dibaca
  kembali oleh `query_impacts()`.
- `Database.init_schema()` menjalankan migrasi idempoten (`ALTER TABLE ... ADD COLUMN`)
  agar DB lama tetap terbuka tanpa menghapus data.

Tanpa kolom ini, berita yang salah rute tetap menghasilkan angka yang tampak valid dan
tidak dapat ditelusuri — melanggar prinsip *explainable* di `DESIGN.md` §1.

## Batasan yang diketahui

1. **Tokenizer hanya bahasa Inggris + stopword Inggris.** Teks Indonesia hanya tertangani
   lewat tahap 1 (kamus). Bila kolektor lokal menghasilkan volume besar, stopword ID
   perlu ditambahkan dan bobot dibangun ulang.
2. **Ambang dari dataset benchmark, bukan berita harian.** Akurasi 94.8%/97.8% diukur
   pada distribusi latih. Performa pada RSS nyata belum diukur; itu perlu set uji
   berlabel manual.
3. **Centroid harus dibangun ulang bila dataset berubah.** Bobot dan router harus
   sepadan; naikkan `version` di `data/router_config.yaml` setiap kali membangun ulang.
4. **Belum ada model `SPX` khusus.** Berita saham umum saat ini jatuh ke fallback
   TF-IDF. Ini celah yang disadari, bukan kelalaian.

## Cara menjalankan

```bash
./venv/bin/python scripts/build_router_centroids.py   # bangun bobot tahap 2
./venv/bin/python -m pytest backend/tests/test_model_router.py -v
```

Pemakaian:

```python
from backend.src.tagging.model_router import ModelRouter

router = ModelRouter()
router.route("Gold hits record as Fed pauses")
# (['finbert_emas', 'fomc_roberta'], 'keyword', 1.0)
```

Integrasi ke penandaan target:

```python
impacts = tagger.route_article(article, sentiment_score=0.4, model_router=router)
# setiap impact membawa routed_from & route_score
```
