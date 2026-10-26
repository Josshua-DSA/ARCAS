# AUDIT v5 — Database, Backend & ML

> Status: audit kode vs `PRD.md` (FR-1..FR-23), `RULES.md`, `SCHEMA.md`
> Tanggal: 2026-10-24 (v5) · Basis: commit `2742e48` (branch `backend/ingest`)
> Lingkup: **hanya** `backend/`, `model/`, `data/`, `scripts/`
> Di luar lingkup: `frontend/` (milik tim GUI)

## Kenapa v5 ini ada

v4 ditulis pada `014cc33` (21 Okt). Sejak itu `main` bergerak 30+ commit dan
**tiga hal besar berubah**, sehingga v4 kini menyesatkan:

1. **`model/fomc/` tidak lagi kosong.** v4 baris 6 menyatakan direktori itu
   "sengaja kosong, jangan disentuh". PR #13 mengisinya: model, kalibrator,
   data loader, bobot, evaluasi, dan 483 baris test. Siapa pun yang membaca v4
   akan mengira ada ruang kosong yang sebenarnya sudah terisi.
2. **`torch` dan `transformers` sudah terdaftar** di `requirements.txt`
   (PR #13). v4 §1 masih menulis "requirements.txt → tidak ada transformers,
   tidak ada torch" sebagai hambatan FR-6. Hambatan itu sudah hilang.
3. **`cli ingest` sudah ada.** v4 §3 dan Langkah 2 mencatatnya sebagai kerja
   yang belum dilakukan. Sekarang selesai; FR-1 naik dari 🟡 ke ✅.

Aturan yang sama seperti v4 tetap berlaku: **setiap baris harus punya bukti
yang bisa dijalankan ulang.** Kalau tidak bisa dibuktikan, tulis "belum
diverifikasi".

---

## Ringkasan Angka (kondisi `2742e48`)

| Metrik | Nilai | Cara verifikasi |
|---|---|---|
| Test | **284 passed, 2 skipped** | `python -m pytest` |
| Berkas test | 28 | `ls backend/tests/test_*.py \| wc -l` |
| mypy | **bersih, 58 file** (backend/src + model) | `mypy` (Python 3.11, mypy 1.11.2) |
| ruff | bersih, 0.17.0 | `ruff check .` |
| Modul `src` | 29 (di luar `__init__`) | `find backend/src -name '*.py' ! -name '__init__.py'` |
| Perintah CLI | 11 | `cli --help` |
| Tabel DB | 15 | `sqlite_master` (bukan 17 seperti v4 — itu salah hitung) |
| Tabel tanpa jalur tulis | 1 | `alloc_profiles` (ditunda, lihat §Yang Masih Kurang) |

Perbandingan dengan v4 (`014cc33`): test 195 → **284**, berkas test 22 → **28**,
mypy 41 → **58** file, CLI 10 → **11** perintah.

**Dua skip yang tersisa adalah disengaja, bukan kegagalan:**

| Test | Alasan skip |
|---|---|
| `test_dedup.py:193` | fixture DB lokal tidak punya duplikat (jalur near-dup diuji di `seeded_pipeline_db`) |
| `test_fomc_pipeline_integration.py:226` | `torch` tidak terpasang di environment ini; jalan penuh di CI |

Catatan: `torch` **ada** di `requirements.txt`, tetapi belum tentu terpasang di
setiap venv lokal. Di venv yang punya torch, test FOMC berjalan penuh dan
suite menjadi jauh lebih lambat.

---

## Status FR — diverifikasi

| FR | P | Status | Bukti / yang kurang |
|---|---|---|---|
| FR-1 Ingest | P0 | ✅ | API (Finnhub/Marketaux/AlphaVantage) + RSS ✅ · **CSV/JSON manual ✅ (`cli ingest`, 21 test)** · scraper ID ❌ (ditunda, tidak memblokir) |
| FR-2 Normalisasi+dedup | P0 | ✅ | SHA-256 exact ✅ · TF-IDF char 3-5gram + cosine ✅ · near-dup terbukti end-to-end (fixture sintetis, uji mutasi) · batas: parafrase sejati → pita tinjauan, bukan digabung |
| FR-3 Penandaan target | P0 | 🟡 | router + impact graph ✅ · `source_registry.yaml` dibaca ✅ · **entitas non-emas belum masuk `asset_aliases`** |
| FR-4 Jam bursa | P0 | ✅ | `compute_effective_trading_date` dipanggil `cleaner.py:99` |
| FR-5 IndoBERT | P3 | ⚪ | MATI 2026-10-11, di luar hitungan |
| FR-6 FinBERT XAU | P0 | ❌ | **satu-satunya FR yang belum disentuh.** `model/xau/src/` = 1 baris docstring, `model/xau/weights/` kosong. Catatan: `torch`+`transformers` sudah tersedia (PR #13), jadi hambatan dependensi sudah hilang |
| FR-7 Baseline TF-IDF | P0 | ✅ | `ModelNotFittedError`; akurasi 93,72% (F1 macro 0,83), 6.882 berita |
| FR-8 Arah per target | P0 | ✅ | `router.py` |
| FR-9 Cap per `basis` | P0 | ✅ | `router_config.yaml` (`explicit_confidence`, `macro_confidence_cap`) |
| FR-10 Agregasi harian | P0 | ✅ | `DailyAggregator.aggregate_for_asset_date` dipanggil `runner.py:397` |
| FR-11 Statistik | P0 | ✅ | OLS Newey-West HAC + Granger; `statsmodels` terpasang; BH-FDR |
| FR-12 Harga & volume | P0 | ✅ | `cli prices` → 66 baris nyata |
| FR-13 SQLite+Parquet | P1 | ✅ | `cli export` → Parquet (commit `6036578`) |
| FR-14 CLI | P1 | ✅ | **11 perintah**: `seed ingest prices pipeline status clean score aggregate stats export report` |
| FR-15 GUI | P1 | — | di luar lingkup |
| FR-16 FOMC track | P1 | ✅ | **BARU (PR #13)**: `model/fomc/src/{model,calibrator,data_loader}.py`, bobot `baseline_fomc.joblib`, `temperature.json`, `evaluate_holdout.py`, `benchmark_results.json`, 483 baris test |
| FR-17 Orkestrasi | P2 | ✅ | `Pipeline.run()` + CLI bertahap |
| FR-18 Alert | P2 | ✅ | tabel `source_health` + `save_source_health` + `sources_needing_alert` + test |
| FR-19 Allocation Tilt | P1 | ✅ | engine ✅ · input dari DB (S-1 diperbaiki) |
| FR-20 Profil alokasi | P1 | 🟡 | YAML ✅ · invarian #10/#11 ditegakkan ✅ · **tabel `alloc_profiles` tanpa CRUD & tanpa pembaca** (ditunda oleh pemilik) |
| FR-21 Persona POV | P1 | ✅ | engine + 5 profil teruji |
| FR-22 Penjelasan | P1 | ✅ | template `rationale` di `persona/engine.py` |
| FR-23 `news_horizon` | P1 | ✅ | ditentukan router + disimpan (commit `b661bdf`) |

**Hitung: ✅ 18 · 🟡 2 · ❌ 1 · ⚪ 1.**
(v4: ✅ 16 · 🟡 5 · ❌ 1 · ⚪ 1.)

---

## Yang Masih Kurang — 3 item, urut dampak

### 1. FR-6 / K-3 · FinBERT XAU belum ada — **P0, satu-satunya yang kosong**

Bukti terukur pada `2742e48`:
```
model/xau/src/__init__.py    -> 1 baris docstring
model/xau/weights/           -> kosong (tidak ada file)
model/xau/evaluation/        -> hanya __init__.py
```

Ini FR P0 dan satu-satunya yang benar-benar belum dikerjakan. Semua sentimen
emas saat ini berasal dari baseline TF-IDF generik, bukan model yang dilatih
pada domain emas. `model_router.py:100` sudah memutuskan track `finbert_emas`
untuk XAU — **router menunjuk ke ruang kosong:**

```python
# backend/src/tagging/model_router.py:100
if ev["gold"] >= self.min_votes and ev["gold"] > ev["fomc"]:
    return ["finbert_emas"], "log_odds", round(ev["mean"], 4)
```

Perhatikan baris berikutnya (`model_router.py:102`): `fomc_roberta` — track
saudaranya — **kini sudah terisi** lewat PR #13. Jadi router punya dua cabang
model; satu hidup, satu mati. Itu membuat FR-6 makin mendesak dan sekaligus
memberi contoh konkret cara mengisinya.

**Perubahan penting sejak v4:** hambatan dependensi **sudah hilang**. PR #13
menambahkan `torch>=2.0.0` dan `transformers>=4.30.0` ke `requirements.txt`.
Yang masih kurang hanya: bobot FinBERT-EMAS, modul inferensi, sambungan ke
`model_router`, mekanisme fallback eksplisit (jangan diam-diam kembali ke
TF-IDF), dan evaluasi pada data berlabel.

**Catatan:** tetap pekerjaan besar (unduh model, latih, evaluasi) — jangan
dicampur dengan perbaikan kecil. Tapi jauh lebih kecil dari perkiraan v4.

**Contoh yang bisa ditiru:** `model/fomc/` (PR #13) sudah memecahkan pola yang
sama untuk track FOMC — `src/model.py`, `src/calibrator.py`, `src/data_loader.py`,
`weights/baseline_fomc.joblib`, `weights/temperature.json`, `evaluation/`,
`benchmark_results.json`, dan `skipif` saat torch tidak ada. Struktur itu bisa
dijadikan cetakan untuk `model/xau/`.

### 2. FR-3 · entitas non-emas belum masuk `asset_aliases` — **P0, parsial**

Bukti: router dan impact graph jalan, `source_registry.yaml` dibaca, tetapi
entitas selain emas belum punya alias di `asset_aliases`. Akibatnya berita
tentang aset non-emas bisa gagal dipetakan ke target yang benar.

### 3. FR-1 sisa · scraper ID (detik/kompas/antara) — **P0, ditunda**

Kanal API + RSS + CSV/JSON manual sudah lengkap. Scraper ID adalah pekerjaan
terpisah yang lebih besar dan **tidak memblokir FR lain** — sengaja ditunda.

---

## Cakupan Test

29 modul `src`. **27 disebut namanya di test; 2 teruji secara tidak langsung:**

| Modul | Kondisi |
|---|---|
| `collect/yfinance_collector.py` | ✅ `test_yfinance_collector.py` (parsing Yahoo terkunci) |
| `collect/news_cli.py` | ✅ `test_news_cli.py` (`_record_health`/`_print_alerts` teruji) |
| `collect/manual_ingest.py` | ✅ `test_manual_ingest.py` (21 test, baru) |
| `normalize/cleaner.py` | 🟡 tidak disebut nama modulnya, tetapi teruji lewat `test_cli_pipeline_real.py` |
| `store/parquet_store.py` | 🟡 tidak disebut nama modulnya, tetapi teruji lewat `test_cli_commands.py` |

Verifikasi: `grep -rl <nama-modul> backend/tests/*.py` → hanya dua di atas yang
tidak cocok. Keduanya tetap tercakup lewat jalur CLI, jadi bukan celah buta —
tetapi tidak ada test unit langsung yang mengunci perilakunya.

Catatan penting dari S-4: test yang menyentuh jalur nyata menemukan dua bug
yang tidak terlihat oleh 190 test lain (`score` membaca `raw_articles`;
`FOREIGN KEY` mentah). **Tambah test jalur nyata, bukan test unit baru.**

---

## Sudah Matang (diverifikasi eksekusi)

| Komponen | Bukti |
|---|---|
| Kolektor berita API | Finnhub 100 item; Marketaux `countries=us`; AlphaVantage `premium_only` terdeteksi |
| Kolektor RSS | 5 feed hidup, RSS 2.0 + Atom, stdlib saja |
| Ranking relevansi | Word-boundary regex; bug `"war"` di "software" sudah mati |
| Kolektor harga | Yahoo chart API; gagal → `PriceFetchError` |
| CRUD 5 tabel berita | Dedup `(source,url)`; run kedua 0 duplikat |
| **Ingest manual** | **`cli ingest --file x.csv\|json`; baris buruk dilewati dengan alasan; idempoten (run kedua 0 baris)** |
| Router 2 tahap | Log-odds Monroe 2008, audit trail `routed_from`/`route_score` |
| StatEngine | Spearman multi-lag, CAR, BH-FDR, OLS HAC, Granger |
| Allocation | Konstrain tepat 100% diuji |
| Pipeline | `raw_articles → articles → sentiments → impacts → daily_sentiment` |
| Health & alert | `source_health` + ambang 3 kegagalan beruntun |
| Normalizer | SHA-256, deteksi bahasa, cut-off UTC non-lookahead |
| **Track FOMC** | **Model + kalibrator + bobot + evaluasi holdout (PR #13)** |
| Schema | 15 tabel, migrasi idempoten |

---

## Urutan Pengerjaan yang Disarankan

**Selesai setelah v4:**
1. ~~FR-2: fixture + uji mutasi near-dup~~ ✅ (`seeded_pipeline_db`).
2. ~~`yfinance_collector` dan `news_cli`: test parsing & alert~~ ✅
   (`test_yfinance_collector.py`, `test_news_cli.py`).
3. ~~FR-20: putuskan hapus atau pindahkan ke tabel~~ → **ditunda oleh pemilik**;
   tabel dibiarkan, invarian #10/#11 diperbaiki ✅.
4. ~~`cli ingest` CSV/JSON + validasi baris buruk~~ ✅ (`backend/ingest`,
   21 test, 284 passed).

**Berikutnya:**

5. **Higiene CI — actions ke Node 24** (15 menit).
   `actions/checkout@v4`, `setup-python@v5`, `docker/*` masih memakai Node 20
   yang sudah deprecated. Belum menggagalkan, tetapi akan keras saat GitHub
   mematikannya. Murah, dan menghindari kegagalan mendadak.
6. **FR-3: `asset_aliases` entitas non-emas** (kecil). Melengkapi P0 yang
   masih parsial.
7. **FR-6 FinBERT XAU** (multi-hari, sendiri). Satu-satunya FR kosong;
   hambatan dependensi sudah hilang, `model/fomc/` bisa jadi cetakan.

**Jangan dikerjakan — sudah selesai:**
K-1, K-2, K-4, K-5, K-6, T-1, T-2, T-3, T-4, T-5, T-7, S-1, S-2, S-3, S-4,
S-5, S-7, FR-1 (kecuali scraper ID), FR-2, FR-4, FR-7, FR-8, FR-9, FR-10,
FR-11, FR-12, FR-13, FR-14, FR-16, FR-17, FR-18, FR-19, FR-21, FR-22, FR-23.

---

## Risiko yang perlu diketahui

1. **`clean` kini wajib sebelum `score`.** Sejak `014cc33`, `score` membaca
   tabel `articles`. Skrip/cron yang memanggil `score` langsung akan berhenti
   dengan exit 1 (dulu jalan diam-diam dengan hasil salah). Ini disengaja.
2. **Data belum cukup untuk statistik.** 2–4 hari berpasangan vs ambang 10.
   `stat_results` tetap kosong sampai ada ~3 bulan data harian.
   **Sejak `cli ingest` ada, data historis bisa dimasukkan lewat CSV** untuk
   mempercepat pengujian end-to-end — tetapi itu data uji, bukan data pasar
   nyata; jangan dipakai untuk menyimpulkan statistik.
3. **`data/finews.db` tidak di-commit** (benar secara keamanan), jadi setiap
   clone mulai dari nol. Kini ada tiga jalur mengisi: API, RSS, dan
   `cli ingest`.
4. **Ambang near-dup belum dikalibrasi.** `NEAR_DUP_THRESHOLD` dipilih tanpa
   data berlabel; setelah FR-2 pun nilainya belum tentu tepat.
5. **FinBERT belum ada = klaim sentimen emas masih generik.** Semua angka
   sentimen XAU saat ini berasal dari model yang tidak dilatih pada domain
   emas. Jangan menyajikan hasil XAU sebagai "analisis khusus emas" sampai
   FR-6 selesai.
6. **Yahoo chart API tidak resmi** — bisa diblokir kapan saja (perilaku benar,
   tapi harga berhenti).
7. **Marketaux free tier** 100 req/hari; HTTP 500 = kuota habis, bukan bug.
8. **AlphaVantage** `NEWS_SENTIMENT` premium — tidak berguna di kunci gratis.
9. **BARU — `torch` membuat CI lambat.** Sejak PR #13, runner CI naik dari
   ~3 menit ke **14 menit** (run `39979672857`) karena memasang `torch` +
   `transformers`. Ini biaya nyata pada kuota CI. Kalau lambat lagi,
   pertimbangkan memasang torch hanya saat job menyentuh `model/**`.
10. **BARU — test FOMC bergantung pada torch.** `test_fomc_pipeline_integration.py`
    memakai `skipif` saat torch tidak ada, jadi suite "hijau" di venv tanpa
    torch tidak membuktikan jalur FOMC berjalan. Jalankan penuh sebelum
    menyentuh `model/fomc/`.

---

## Catatan Metodologi

Klaim v5 diverifikasi dengan eksekusi pada `2742e48`:

- `git rev-parse --short HEAD` → `2742e48`
- `pytest` → **284 passed, 2 skipped**
- `ls backend/tests/test_*.py | wc -l` → 28
- `find backend/src -name '*.py' ! -name '__init__.py' | wc -l` → 29
- `mypy` (venv bersih Python 3.11, mypy 1.11.2, ruff 0.17.0) →
  **Success, 58 source files**
- `ruff check .` → All checks passed
- `cli --help` → 11 perintah, termasuk `ingest` (baru)
- `find model/xau -name '*.py' -o -name '*.json' -o -name '*.joblib'` →
  hanya 3 `__init__.py`, membuktikan FR-6 masih kosong
- `ls model/fomc/src/*.py model/fomc/weights/*` → 4 modul + 2 bobot,
  membuktikan FR-16 terisi
- `gh run list --branch main` → run `39979672857` success dalam 14m8s
  (bukti risiko #9)

**Koreksi terhadap v4:**

| Klaim v4 | Kondisi sebenarnya |
|---|---|
| Baris 6: "`model/fomc/` sengaja kosong, jangan disentuh" | **Salah.** Terisi sejak PR #13 |
| §1: "`requirements.txt` → tidak ada transformers, tidak ada torch" | **Salah.** Ada sejak PR #13 |
| §3 + Langkah 2: "`cli ingest` tidak ada" | **Salah.** Ada sejak `backend/ingest` |
| "Tabel DB: 17" | **Salah hitung.** Nyata 15 (`sqlite_master`) |
| "Modul tanpa test: 2" | Masih benar, tetapi modulnya kini `cleaner` + `parquet_store` |

Klaim v4 yang **tetap benar**: FR-6 kosong, FR-3 parsial, FR-20 ditunda,
`stat_results` kosong karena data kurang.
