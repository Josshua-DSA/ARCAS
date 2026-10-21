# AUDIT v4 — Database, Backend & ML

> Status: audit kode vs `PRD.md` (FR-1..FR-23), `RULES.md`, `SCHEMA.md`
> Tanggal: 2026-10-21 (v4) · Basis: commit `014cc33` · 15 commit sejak `e1f00f2`
> Lingkup: **hanya** `backend/`, `model/`, `data/`, `scripts/`
> Di luar lingkup: `frontend/` (milik tim GUI) · `model/fomc/` (sengaja kosong, jangan disentuh)

## Kenapa v4 ini ada

v3 rusak secara internal dan menyesatkan. Dua masalahnya:

1. **Bertentangan dengan dirinya sendiri.** Blok "Status pelaksanaan" v3
   (baris 9–20) menyatakan K-1/K-4/K-5/K-6/T-7/S-4 selesai, tetapi tabel FR
   (baris 84–107) dan blok "Yang berubah sejak v1" (baris 114–125) masih
   menulis item yang sama sebagai ❌. Body v3 adalah **kondisi v2 asli yang
   tidak pernah diperbarui** — hanya bagian atas yang diperbarui.
2. **Klaim tidak diverifikasi.** Saat diperiksa satu per satu ke kode, 16 dari
   ~20 item "terbuka" ternyata sudah selesai.

Akibatnya: siapa pun yang bekerja dari body v3 akan mengerjakan ulang hal yang
sudah beres. Dokumen ini menggantikan seluruh v3 — angka di bawah **semua
diperiksa ulang dengan `grep` dan eksekusi**, bukan disalin.

Aturan untuk revisi berikutnya: **setiap baris harus punya bukti yang bisa
dijalankan ulang**. Kalau tidak bisa dibuktikan, tulis "belum diverifikasi".

---

## Ringkasan Angka (kondisi `014cc33`)

| Metrik | Nilai | Cara verifikasi |
|---|---|---|
| Test | **195 passed, 1 skipped** | `python -m pytest backend/tests` |
| Berkas test | 22 | `ls backend/tests/test_*.py` |
| mypy | **bersih, 41 file** | `mypy backend/src` |
| ruff | bersih | `ruff check backend/src backend/tests` |
| Modul `src` | 28 (di luar `__init__`) | `find backend/src -name '*.py'` |
| Modul tanpa test | 2 | lihat §Cakupan Test |
| Tabel DB | 17 | `sqlite_master` |
| Tabel tanpa jalur tulis | 1 | `alloc_profiles` |

Isi `data/finews.db` saat audit:

```
raw_articles      67     articles          54
sentiments        54     article_targets   20
impacts           20     daily_sentiment   10
prices            66     source_health     14
asset_master       3     asset_aliases     16
stat_results       0     labels             0
persona_views      0     alloc_suggestions  0
alloc_profiles     0     api_quota_usage    1
```

`stat_results = 0` **bukan bug**: `cli stats` melaporkan tiap aset punya 2–4
hari berpasangan, sedangkan `MIN_OBS_OLS = 10`. Data belum cukup, dan kode
menolak mengarang hasil — perilaku yang benar.

---

## Status FR — diverifikasi

| FR | P | Status | Bukti / yang kurang |
|---|---|---|---|
| FR-1 Ingest | P0 | 🟡 | API (Finnhub/Marketaux/AlphaVantage) + RSS ✅ · **CSV/JSON/manual ❌** · scraper ID ❌ (tidak ada modul) |
| FR-2 Normalisasi+dedup | P0 | 🟡 | SHA-256 exact ✅ · TF-IDF char 3-5gram + cosine ✅ · **near-dup tidak terbukti** (test di-skip) |
| FR-3 Penandaan target | P0 | 🟡 | router + impact graph ✅ · `source_registry.yaml` dibaca ✅ · **entitas non-emas belum masuk `asset_aliases`** |
| FR-4 Jam bursa | P0 | ✅ | `compute_effective_trading_date` dipanggil `cleaner.py:99` |
| FR-5 IndoBERT | P3 | ⚪ | MATI 2026-10-11, di luar hitungan |
| FR-6 FinBERT XAU | P0 | ❌ | **satu-satunya FR yang benar-benar belum disentuh** |
| FR-7 Baseline TF-IDF | P0 | ✅ | `ModelNotFittedError`; akurasi 93,72% (F1 macro 0,83), 6.882 berita |
| FR-8 Arah per target | P0 | ✅ | `router.py` |
| FR-9 Cap per `basis` | P0 | ✅ | `router_config.yaml` (`explicit_confidence`, `macro_confidence_cap`) |
| FR-10 Agregasi harian | P0 | ✅ | `DailyAggregator.aggregate_for_asset_date` dipanggil `runner.py:397` |
| FR-11 Statistik | P0 | ✅ | OLS Newey-West HAC + Granger; `statsmodels` terpasang; BH-FDR |
| FR-12 Harga & volume | P0 | ✅ | `cli prices` → 66 baris nyata |
| FR-13 SQLite+Parquet | P1 | ✅ | `cli export` → Parquet (commit `6036578`) |
| FR-14 CLI | P1 | ✅ | 10 perintah: `seed prices pipeline status clean score aggregate stats export report` |
| FR-15 GUI | P1 | — | di luar lingkup |
| FR-17 Orkestrasi | P2 | ✅ | `Pipeline.run()` + CLI bertahap |
| FR-18 Alert | P2 | ✅ | tabel `source_health` + `save_source_health` + `sources_needing_alert` + test |
| FR-19 Allocation Tilt | P1 | ✅ | engine ✅ · input dari DB (S-1 diperbaiki) |
| FR-20 Profil alokasi | P1 | 🟡 | YAML ✅ · **tabel `alloc_profiles` tanpa CRUD & tanpa pembaca** |
| FR-21 Persona POV | P1 | ✅ | engine + 5 profil teruji |
| FR-22 Penjelasan | P1 | ✅ | template `rationale` di `persona/engine.py` |
| FR-23 `news_horizon` | P1 | ✅ | ditentukan router + disimpan (commit `b661bdf`) |

**Hitung: ✅ 16 · 🟡 5 · ❌ 1 · ⚪ 1.**
(v3 menulis ✅ 3 · 🟡 15 · ❌ 3 — usang.)

---

## Yang Masih Kurang — 4 item, urut dampak

### 1. FR-6 / K-3 · FinBERT XAU belum ada — **P0, satu-satunya yang kosong**

Bukti:
```
model/xau/src/__init__.py   -> 1 baris docstring
model/xau/weights/          -> kosong
model/xau/evaluation/       -> hanya __init__.py
requirements.txt            -> tidak ada transformers, tidak ada torch
```

Ini FR P0 dan satu-satunya yang benar-benar belum dikerjakan. Semua sentimen
emas saat ini berasal dari baseline TF-IDF generik, bukan model yang dilatih
pada domain emas. `model_router.py:100` sudah memutuskan track `finbert_emas`
untuk XAU — router menunjuk ke ruang kosong.

**Yang harus dikerjakan:** siapkan bobot FinBERT-EMAS, tulis modul inferensi,
daftarkan `transformers` + `torch`, sambungkan ke `model_router`, beri
mekanisme fallback eksplisit bila bobot tidak ada (jangan diam-diam kembali ke
TF-IDF), lalu evaluasi pada data berlabel.

**Catatan:** ini pekerjaan besar (unduh model, latih, evaluasi) — jangan
dicampur dengan perbaikan kecil.

### 2. FR-2 · near-duplicate tidak terbukti bekerja — **P0, biaya kecil**

Bukti: `test_dedup.py:193` → `pytest.skip("data uji tidak punya duplikat")`.
Fixture `pipeline_db` tidak berisi pasangan yang mirip, jadi jalur
`NearDuplicateDetector` **tidak pernah dieksekusi** di test mana pun.

Ini pola yang sama dengan S-4: test yang tidak pernah terbukti bisa gagal
bukan bukti apa pun. Kodenya ada (`TF-IDF char 3-5gram + cosine`, dipanggil
`runner.py:246`), tetapi belum ada bukti ia menandai duplikat dengan benar.

**Yang harus dikerjakan:** fixture dengan 2 artikel parafrase (judul sama,
sumber beda, badan diparafrase) → pastikan `duplicate_of` terisi, duplikat
tidak menambah `n_articles`, dan artikel berbeda tetap lolos. Lalu uji mutasi:
matikan detektor, test harus gagal.

### 3. FR-1 · ingest CSV/JSON/manual belum ada — **P0, parsial**

Bukti: CLI tidak punya perintah `ingest`; tidak ada pembaca CSV/JSON untuk
input manual. Kanal utama (API + RSS) sudah jalan dan teruji.

**Yang harus dikerjakan:** perintah `cli ingest --file x.csv|json` yang
memetakan kolom ke `raw_articles`, plus validasi baris buruk (dilewati dengan
alasan, bukan crash). Scraper ID (detik/kompas/antara) terpisah dan lebih
besar — bisa ditunda tanpa memblokir FR lain.

### 4. FR-20 · tabel `alloc_profiles` mati — **P1, kosmetik arsitektur**

Bukti: tabel dibuat di skema, **nol CRUD**, **nol pembaca**. Fungsinya jalan
lewat `alloc_profiles.yaml`.

**Yang harus dikerjakan:** pilih satu — (a) hapus tabelnya, atau (b) pindahkan
profil dari YAML ke tabel + CRUD. Jangan biarkan keduanya ada tanpa keterangan;
pembaca baru akan mengira tabel itu sumber kebenaran.

---

## Cakupan Test

24 dari 28 modul `src` disebut di test. Dua yang tidak punya test sama sekali:

| Modul | Kondisi | Risiko |
|---|---|---|
| `collect/yfinance_collector.py` | tanpa test; hanya `PriceFetchError` diuji lewat jalur lain | sedang — parsing Yahoo tidak terkunci |
| `collect/news_cli.py` | tanpa test; `_record_health`/`_print_alerts` tidak diuji | sedang — logika alert FR-18 tanpa test |

`normalize/cleaner.py` dan `store/parquet_store.py` **bukan** tanpa test —
keduanya teruji lewat `test_cli_pipeline_real.py` dan `test_cli_commands.py`.

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
| Router 2 tahap | Log-odds Monroe 2008, audit trail `routed_from`/`route_score` |
| StatEngine | Spearman multi-lag, CAR, BH-FDR, OLS HAC, Granger |
| Allocation | Konstrain tepat 100% diuji |
| Pipeline | `raw_articles → articles → sentiments → impacts → daily_sentiment` |
| Health & alert | `source_health` + ambang 3 kegagalan beruntun |
| Normalizer | SHA-256, deteksi bahasa, cut-off UTC non-lookahead |
| Schema | 17 tabel, migrasi idempoten |

---

## Urutan Pengerjaan yang Disarankan

**Langkah 1 — murah, nilai langsung (½ hari)**
1. FR-2: fixture parafrase + uji mutasi near-dup.
2. `yfinance_collector` dan `news_cli`: test parsing & alert.
3. FR-20: putuskan hapus atau pindahkan ke tabel.

**Langkah 2 — FR-1 sisa (1 hari)**
4. `cli ingest` CSV/JSON + validasi baris buruk.

**Langkah 3 — FR-6 FinBERT (multi-hari, sendiri)**
5. Bobot, modul inferensi, `transformers`/`torch`, sambung ke `model_router`,
   fallback eksplisit, evaluasi.

**Jangan dikerjakan — sudah selesai pada `014cc33`:**
K-1, K-2, K-4, K-5, K-6, T-1, T-2, T-3, T-4, T-5, T-7, S-1, S-2, S-3, S-4,
S-5, S-7, FR-4, FR-7, FR-8, FR-9, FR-10, FR-11, FR-12, FR-13, FR-14, FR-17,
FR-18, FR-19, FR-21, FR-22, FR-23.

---

## Risiko yang perlu diketahui

1. **`clean` kini wajib sebelum `score`.** Sejak `014cc33`, `score` membaca
   tabel `articles`. Skrip/cron yang memanggil `score` langsung akan berhenti
   dengan exit 1 (dulu jalan diam-diam dengan hasil salah). Ini disengaja.
2. **Data belum cukup untuk statistik.** 2–4 hari berpasangan vs ambang 10.
   `stat_results` tetap kosong sampai ada ~3 bulan data harian.
3. **`data/finews.db` tidak di-commit** (benar secara keamanan), jadi setiap
   clone mulai dari nol dan harus menjalankan ingest sendiri.
4. **Ambang near-dup belum dikalibrasi.** `NEAR_DUP_THRESHOLD` dipilih tanpa
   data berlabel; setelah FR-2 pun nilainya belum tentu tepat.
5. **FinBERT belum ada = klaim sentimen emas masih generik.** Semua angka
   sentimen XAU saat ini berasal dari model yang tidak dilatih pada domain
   emas. Jangan menyajikan hasil XAU sebagai "analisis khusus emas" sampai
   FR-6 selesai.
6. **Yahoo chart API tidak resmi** — bisa diblokir kapan saja; `fetch_prices`
   akan melempar error (perilaku benar, tapi harga berhenti).
7. **Marketaux free tier** 100 req/hari; HTTP 500 = kuota habis, bukan bug.
8. **AlphaVantage** `NEWS_SENTIMENT` premium — tidak berguna di kunci gratis.

---

## Catatan Metodologi

Semua klaim v4 diverifikasi dengan eksekusi, bukan pembacaan kode saja:

- `grep -rn <simbol> backend/src/` untuk 12 komponen → semua punya pemanggil
  (`process_raw` 4, `route_article` 2, `save_price` 1, `ParquetStore` 3,
  `ReportExporter` 4, `NearDuplicateDetector` 2)
- `re.findall` pada `db.py` untuk `INSERT INTO` → 16/17 tabel; sisa
  `alloc_profiles`
- `sqlite3` hitung 17 tabel `data/finews.db` → angka di atas
- `python -m backend.src.cli stats` → "2–4 hari berpasangan, butuh >= 10"
- `python -m backend.src.cli --help` → 10 perintah
- `pytest backend/tests` → 195 passed, 1 skipped
- `mypy backend/src` → 41 file, 0 error
- Peta modul→test via regex nama modul pada seluruh `test_*.py` → 24/28

**Koreksi terhadap v3:** tabel "pemanggil" di v3 (K-1) menyebut 10 komponen
dengan 0 pemanggil. Diukur ulang pada `014cc33`, **semuanya punya pemanggil** —
tabel itu menggambarkan kondisi v2 dan tidak boleh dipakai lagi.
