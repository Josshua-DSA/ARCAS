# AUDIT v2 — Database, Backend & ML

> Status: audit kode vs `PRD.md` (FR-1..FR-23), `RULES.md`, `SCHEMA.md`
> Tanggal: 2026-10-21 (v2) · Basis: `acb2171` + pekerjaan belum di-commit
> Lingkup: **hanya** `backend/`, `model/`, `data/`, `scripts/`
> Di luar lingkup: `frontend/` (milik tim GUI) · `model/fomc/` (sengaja kosong, jangan disentuh)

## ⚠️ Status pelaksanaan — Fase 1 SELESAI 2026-10-21

Fase 1 ("Sambungkan pipa") sudah dikerjakan dan diverifikasi. Ringkasnya:

| Item | Status | Bukti |
|---|---|---|
| **K-1** pipa tersambung | ✅ selesai | `backend/src/pipeline/runner.py` (baru) — `raw_articles → articles → sentiments → impacts → daily_sentiment` jalan |
| **K-4** degradasi senyap baseline | ✅ selesai | `ModelNotFittedError`; baseline dilatih nyata **akurasi 93,72%** (F1 macro 0,83) dari 6.882 berita |
| **K-5** `save_price` yatim | ✅ selesai | `cli.py prices` → **66 baris harga nyata** tersimpan |
| **K-6** `/api/universe` kosong | ✅ selesai | `seed_asset_master`+`seed_aliases` dipanggil di `Pipeline.seed_universe()` |
| **T-7** CI merah (`pyarrow`/`openpyxl`) | ✅ selesai | Masuk `requirements.txt`; CI juga melatih baseline |
| **S-4** tak ada test jalur nyata | ✅ selesai | `test_pipeline_integration.py` — 7 test end-to-end |

**Isi database sekarang** (`python -m backend.src.cli status`):

```
✅ raw_articles 38   ✅ articles 38   ✅ article_targets 14
✅ sentiments 38     ✅ impacts 14    ✅ daily_sentiment 6
✅ prices 66         ✅ asset_master 3 ✅ asset_aliases 16
   stat_results 0    labels 0    alloc_profiles 0    alloc_suggestions 0    persona_views 0
```

Test: **71 passed**, ruff bersih. Bug baru yang ditemukan & diperbaiki saat
pengerjaan: `n_sources` di `DailyAggregator` hardcode `1` (XAU punya 7 artikel
dari 3 sumber, dilaporkan 1 sumber).

**Sisa untuk fase berikutnya:** K-2 (3 tabel tanpa penulisan), K-3 (FinBERT),
T-1..T-6, S-1..S-7 — lihat "Urutan Pengerjaan" di bawah.

---

## Ringkasan Angka (kondisi awal audit v2)

| Metrik | v1 | v2 | Δ |
|---|---|---|---|
| LOC `backend/src` | 3.282 | **4.586** | +1.304 |
| Test | 31 (8 file) | **62 (11 file)** | +31 |
| Tabel skema | 14 | 14 | — |
| Tabel punya `INSERT` | 11 | 11 | — |
| Tabel **berisi data** | 0 | **1 dari 14** | +1 |
| File DB fisik | tidak ada | **ada** (`data/finews.db`) | ✅ |
| FR terpenuhi penuh | 11/23 | **7/23** | −4 \* |

\* Angka FR turun bukan karena ada yang rusak. v1 menghitung "kode ada" sebagai
"terpenuhi". Audit v2 memakai definisi lebih ketat: **terpenuhi = kode lengkap
DAN tersambung ke alur nyata**. Dengan definisi v1, angkanya 13/23. Penurunan
ini adalah koreksi pengukuran, bukan kemunduran.

**Kesimpulan satu baris:** pengumpulan data sudah hidup dan menyimpan, tetapi
**belum ada satu pun kode yang membaca `raw_articles` lalu memprosesnya** —
pipa berhenti tepat setelah "berita masuk".

---

## Status FR — jujur per item

| FR | P | Status | Bukti / yang kurang |
|---|---|---|---|
| FR-1 Ingest | P0 | 🟡 | API + RSS ✅ · scraper ID, CSV/JSON, manual ❌ |
| FR-2 Normalisasi+dedup | P0 | 🟡 | SHA-256 exact ✅ · near-dup embedding ❌ |
| FR-3 Penandaan target | P0 | 🟡 | router + impact graph ✅ · `source_registry.yaml` tak dibaca ❌ |
| FR-4 Jam bursa | P0 | 🟡 | `compute_effective_trading_date` ada ✅ · tak dipanggil alur ❌ |
| FR-5 IndoBERT | P3 | ⚪ | MATI 2026-10-11, di luar hitungan |
| FR-6 FinBERT XAU | P0 | ❌ | `model/xau/src/__init__.py` = 1 baris docstring |
| FR-7 Baseline TF-IDF | P0 | 🟡 | kode ada, tapi degradasi senyap (K-4) |
| FR-8 Arah per target | P0 | ✅ | `router.py:115-119` |
| FR-9 Cap per `basis` | P0 | 🟡 | cap hardcoded literal, bukan kebijakan (T-5) |
| FR-10 Agregasi harian | P0 | 🟡 | `DailyAggregator` ada, **0 pemanggil** |
| FR-11 Statistik | P0 | 🟡 | Spearman/CAR/BH ✅ · OLS HAC + Granger ❌ |
| FR-12 Harga & volume | P0 | 🟡 | `PriceCollector` ✅ · `save_price` 0 pemanggil |
| FR-13 SQLite+Parquet | P1 | 🟡 | SQLite ✅ · `ParquetStore` 0 pemanggil |
| FR-14 CLI | P1 | 🟡 | hanya `identify`/`health`/`fetch` |
| FR-15 GUI | P1 | — | di luar lingkup |
| FR-17 Orkestrasi | P2 | ❌ | tidak ada `run_pipeline()` |
| FR-18 Alert | P2 | ❌ | tabel `source_health` tak ada |
| FR-19 Allocation Tilt | P1 | 🟡 | engine ✅ · input hardcoded (S-1) |
| FR-20 Profil alokasi | P1 | 🟡 | YAML ✅ · tabel `alloc_profiles` tanpa CRUD |
| FR-21 Persona POV | P1 | ✅ | engine + 5 profil teruji |
| FR-22 Penjelasan | P1 | ✅ | template `rationale` di persona engine |
| FR-23 `news_horizon` | P1 | 🟡 | field ada, router tak pernah mengisi → selalu `SHORT` |

**Hitungan:** ✅ 3 (FR-8, FR-21, FR-22) · 🟡 15 · ❌ 3 (FR-6, FR-17, FR-18) · ⚪ 1 · — 1.
Dengan definisi longgar v1 (kode ada = terpenuhi): ✅ 13.

---

## Yang berubah sejak v1

| Item v1 | Status | Bukti |
|---|---|---|
| K-2 file DB belum ada | ✅ selesai | `data/finews.db`, 14 tabel, 38 baris berita |
| K-3 10 tabel tanpa jalur tulis | ✅ sebagian besar | +CRUD `raw_articles`/`articles`/`article_targets`/`sentiments`/`labels`; sisa 3 (K-2) |
| K-5 tidak ada kolektor berita | ✅ selesai | `news_api/` (3 penyedia) + `rss_collector.py` (5 feed) |
| — fallback sintetis harga | ✅ selesai | gagal → `PriceFetchError`, bukan `np.random.normal` |
| K-1 orkestrasi | ❌ masih | lihat K-1 |
| K-4 FinBERT | ❌ masih | lihat K-3 |
| K-6 degradasi senyap baseline | ❌ masih | lihat K-4 |
| T-4 `source_registry` tak dibaca | ❌ masih | lihat T-4 |

---

# 🔴 KRITIS

## K-1 · Tidak ada kode yang memproses `raw_articles`

Temuan terpenting v2. Data mentah masuk, tetapi **tidak ada kelanjutannya**.

Dihitung dari pemanggil nyata di `backend/src/` (`grep`, di luar definisi & test):

| Komponen | Pemanggil di `src/` |
|---|---|
| `ArticleCleaner.process_raw()` | **0** |
| `TargetRouter.route()` | **0** |
| `DailyAggregator.aggregate_*()` | **0** |
| `StatEngine.*` | **0** |
| `ReportExporter` | **0** |
| `ParquetStore` | **0** |
| `.save_price()` | **0** |
| `.save_impact()` | **0** |
| `.save_daily_sentiment()` | **0** |
| `.save_stat()` | **0** |
| `.save_raw_articles()` | **1** (`news_cli.py:128`) |

Alur berhenti di kotak kedua:

```
collect → raw_articles → [STOP] → articles → sentiments → impacts → daily → stats → report
   ✅         ✅            ❌        ❌         ❌          ❌        ❌      ❌       ❌
```

`data/finews.db`: **38 baris di `raw_articles`, 0 di 13 tabel lain** (diverifikasi
`sqlite3` per tabel).

**Dampak:** semua endpoint API kecuali `/health` mengembalikan kosong. Tidak ada
`run_pipeline()`, tidak ada CLI untuk `clean/score/aggregate/stats/report` (FR-14).
`normalize/`, `tagging/`, `aggregate/`, `stats/`, `report/` tidak punya
`__main__` maupun `argparse` sama sekali.

## K-2 · 3 dari 14 tabel masih tanpa jalur tulis

Dipetakan dari `INSERT INTO` di `db.py` — **bukan** dari nama method, karena
`save_stat` dan `seed_asset_master` tidak mengikuti pola `save_<tabel>`:

| Tabel | `INSERT` | Keterangan |
|---|---|---|
| `raw_articles` | ✅ | `save_raw_article(s)` |
| `articles` | ✅ | `save_article(s)` |
| `article_targets` | ✅ | `save_article_target(s)` |
| `sentiments` | ✅ | `save_sentiment` |
| `impacts` | ✅ | `save_impact` |
| `daily_sentiment` | ✅ | `save_daily_sentiment` |
| `prices` | ✅ | `save_price` |
| `stat_results` | ✅ | `save_stat` |
| `labels` | ✅ | `save_label(s)` |
| `asset_master` | ✅ | `seed_asset_master` |
| `asset_aliases` | ✅ | `seed_aliases` |
| `alloc_profiles` | ❌ | **tidak ada** |
| `alloc_suggestions` | ❌ | **tidak ada** |
| `persona_views` | ❌ | **tidak ada** |

11/14 punya jalur tulis, tetapi **7 di antaranya belum pernah dipanggil** (K-1).
Punya method ≠ terpakai.

## K-3 · FinBERT (XAU) belum ada

`model/xau/src/__init__.py` berisi **1 baris docstring**. `transformers` dan
`torch` tidak ada di `requirements.txt` dan tidak terinstall.

`model_router.py` sudah memutuskan `finbert_emas` untuk XAU, tetapi model yang
dipilih belum ada — router menunjuk ke ruang kosong.

> **Di luar lingkup:** `model/fomc/` tetap kosong dan tidak boleh disentuh.
> Track ML hanya `model/xau/`.

## K-4 · Degradasi senyap pada baseline (belum diperbaiki)

`scikit-learn` **tidak ada** di `requirements.txt` dan tidak terinstall.
`baseline.py` menangkap `ImportError` → `TfidfVectorizer = None`, lalu
`predict_probs()` diam-diam mengembalikan prior konstan.

Diuji ulang sekarang:

```
BaselineTfidfSentiment().predict_probs(["Gold rallied on Fed cut"])
→ p_pos=0.2 p_neu=0.6 p_neg=0.2
```

Tanpa exception, tanpa warning. Test tetap **hijau**.

**Dampak:** test memberi rasa aman palsu. Ini kelas bug yang sama dengan fallback
`np.random.normal` yang sudah dibereskan di collector harga — untuk konsistensi,
`predict_probs()` tanpa model terlatih harus **melempar**, bukan mengarang
distribusi.

## K-5 · Jalur A (harga) tidak menyimpan apa pun

`PriceCollector` berfungsi — data nyata terverifikasi (XAU 4160.10,
RATE_UST 5.117, SPX 7712.57) — tetapi `save_price()` **tidak punya pemanggil**.
`news_cli.py` hanya menulis berita.

**Dampak:** `prices` kosong → `query_prices()` kosong → Spearman & CAR tidak akan
pernah bisa dihitung karena tidak ada sisi harga.

## K-6 · `asset_master` kosong → `/api/universe` mengembalikan `[]`

`seed_asset_master()` dan `seed_aliases()` ada dan lengkap, tetapi **tidak pernah
dipanggil** — bukan oleh CLI, bukan oleh `app.py`, bukan oleh test alur nyata.

Diuji pada `data/finews.db`:

```
asset_master: 0 baris
get_active_universe()  → []
get_meta_summary()     → {'universe_count': 0, 'targets': [], ...}
```

`/api/universe` membaca `get_active_universe()` → **kosong**, padahal universe
terkunci 3 aset. `is_valid_target("XAU")` masih `True` hanya karena hardcode
fallback `{"XAU","RATE_UST","SPX"}` di `db.py:848` — validasi lolos bukan karena
data, tapi karena cadangan di kode.

**Dampak:** semua endpoint `/api/*/{target}` melewati validasi, lalu query ke
tabel kosong dan mengembalikan `[]`. Tampak "berfungsi", sebenarnya tidak ada data.

---

# 🟠 TINGGI

## T-1 · FR-11 — OLS Newey-West HAC & Granger belum ada

`StatEngine` hanya punya `benjamini_hochberg`, `compute_car_event_study`,
`compute_spearman_lags`, `frame_from_daily_prices`. `statsmodels` tidak ada di
`requirements.txt` **dan** tidak terinstall.

`schema.py` menyiapkan `test: str  # pearson | spearman | ols | granger | event_study`
— implementasi `ols` dan `granger` kosong.

## T-2 · FR-14 — CLI baru mencakup `collect`

`news_cli.py` punya `identify`, `health`, `fetch` — semuanya soal berita.
Tidak ada `clean`, `score`, `aggregate`, `stats`, `report`.

`RULES.md:144` mewajibkan CLI `report` mengekspor `outputs/report.html`
mandiri. `ReportExporter` ada, tapi tidak ada CLI yang memanggilnya.

## T-3 · FR-18 — Alert & tabel `source_health` belum ada

`source_health` hanya muncul di **komentar docstring** `yfinance_collector.py:35`,
bukan tabel, bukan kode. Tidak ada notifikasi kegagalan sumber.

Kesehatan sumber sekarang dilaporkan *saat dijalankan* (`health()` mengembalikan
status per feed/penyedia), tetapi **tidak dipersistensikan** — jadi tidak ada
riwayat "feed ini mati sejak kapan".

## T-4 · FR-3 — `source_registry.yaml` masih tidak dibaca kode

Saya baru memperbarui isi YAML-nya (URL mati diganti, penyedia API
didokumentasikan), tetapi **kode masih hardcode**:

| Lokasi | Isi | Sumber sebenarnya |
|---|---|---|
| `news_api/keywords.py` | `TARGET_KEYWORDS` (15/22/17 kata) | YAML `targets.<ID>.keywords` (9/8/8) |
| `rss_collector.py` | `FEEDS` dict | YAML `targets.<ID>.feeds` |

Docstring `keywords.py:3` menulis *"Bersumber dari `data/source_registry.yaml`"*,
padahal nilainya disalin manual. Ini **dokumen yang berbohong** — lebih buruk
daripada tidak ada dokumen, karena orang akan mengedit YAML lalu bingung kenapa
tidak ada efeknya.

Dua sumber kebenaran yang **sudah** menyimpang: kata kunci di kode 7–14 item
lebih banyak dari YAML, dan tidak ada satu pun kata YAML yang absen dari kode
(arah penyimpangan satu sisi, tapi tetap akan makin parah).

## T-5 · FR-9 — Confidence cap masih literal, bukan kebijakan

`RULES.md` §1.2 menetapkan cap per `basis`: `explicit` 1.00, `macro_factor` 0.85,
`sector_inferred` 0.60 (dicoret di MVP). Di kode, cap itu **angka ajaib**:

```python
# tagging/router.py:135
confidence=0.88,  # Under explicit cap 1.00
# tagging/router.py:174
confidence=min(0.85, 0.50 + weight * 0.35),  # Cap 0.85
```

Tidak ada tabel kebijakan, tidak ada pembacaan dari config/YAML — melanggar
`RULES.md` §"Tidak ada magic number". `sector_inferred` tidak diimplementasi.

## T-6 · FR-2 — Near-duplicate detection belum ada

Dedup sekarang **hanya exact** (`sha256(norm(title)+norm(body))[:16]`).
"Gold rises 2%" dan "Gold climbs 2%" adalah dua artikel berbeda. PRD meminta
exact **+ embedding near-dup**. Relevan secara praktis: feed berbeda sering
memuat rilis yang sama.

## T-7 · CI remote akan gagal: `pyarrow` & `openpyxl` tidak di `requirements.txt`

CI menjalankan `pip install -r requirements.txt` lalu `pytest`. Di venv lokal
`pyarrow 26.0.0` dan `openpyxl` kebetulan ada, jadi test lulus — **tapi CI
memasang dari requirements saja**:

```
backend/tests/test_model_router.py:62  pd.read_parquet(...)  → butuh pyarrow
backend/tests/test_model_router.py:63  pd.read_excel(...)    → butuh openpyxl
```

`grep -c "pyarrow\|openpyxl" requirements.txt` → **0**. Ini persis penyebab CI
merah yang sudah tercatat (`ModuleNotFoundError: No module named 'pyarrow'`), dan
**masih belum diperbaiki**. Lulus lokal ≠ lulus CI.

---

# 🟡 SEDANG

## S-1 · Angka hardcoded di dua endpoint API

```python
# serve/app.py:166 — /api/allocation
scores = {"XAU": (0.25, 0.70), "SPX": (0.20, 0.80), "RATE_UST": (0.10, 0.65)}
# serve/app.py:182 — /api/persona/{article_id}
score: float = 0.35, confidence: float = 0.75
```

Komentar di kode sendiri mengakui: *"In full run: pulls latest daily sentiment
score for key assets"*. Endpoint menyajikan simulasi sebagai hasil analisis.

## S-2 · `persona_views` & `alloc_suggestions` dihitung tapi tidak disimpan

Keduanya dipakai `AllocationEngine`/`PersonaEngine` dan dikembalikan lewat API,
lalu dibuang. Tidak bisa diaudit ulang, tidak reproducible — padahal NFR
mewajibkan reproducibility.

## S-3 · `ParquetStore` dan `ReportExporter` yatim

Keduanya berfungsi, tetapi tidak dipanggil siapa pun. `ReportExporter` bahkan
**tanpa test**.

## S-4 · Cakupan test tidak menyentuh jalur nyata

62 test hijau, tetapi tidak ada satu pun yang menguji
`raw_articles → articles → … → impacts`. Semua test memakai `tmpdir`. Inilah
sebabnya K-1 tidak terdeteksi: setiap komponen diuji sendiri-sendiri, tidak ada
yang menguji sambungannya.

## S-5 · `news_horizon` selalu `SHORT`

`TargetImpact.news_horizon` punya default `NewsHorizon.SHORT`, dan
`tagging/router.py` **tidak pernah mengisinya**. FR-23 secara teknis "terisi",
praktisnya konstanta.

## S-6 · FR-1 belum lengkap: tidak ada ingest CSV/JSON/manual

Yang ada hanya API + RSS. `scraper ID`, `file CSV/JSON`, dan `input manual`
belum ada.

## S-7 · `init_tables()` adalah alias `init_schema()`

Dua nama untuk satu fungsi. `app.py` memanggil `init_tables()`, CLI memanggil
`init_schema()`. Tidak berbahaya, tapi membingungkan pembaca baru — dan
menyembunyikan fakta bahwa keduanya idempoten.

---

# ✅ Sudah Matang (diverifikasi eksekusi)

| Komponen | Bukti |
|---|---|
| **Kolektor berita API** | Finnhub 100 item; Marketaux `countries=us`; AlphaVantage `premium_only` terdeteksi, bukan crash |
| **Kolektor RSS** | 5 feed hidup, RSS 2.0 + Atom, stdlib saja |
| **Ranking relevansi** | Word-boundary regex; bug `"war"` di "software" sudah mati |
| **Kolektor harga** | Yahoo chart API; gagal → `PriceFetchError` (bukan data acak) |
| **CRUD 5 tabel berita** | Dedup `(source,url)`; run kedua menyimpan 0 duplikat |
| **Router 2 tahap** | Log-odds Monroe 2008, audit trail `routed_from`/`route_score` |
| **StatEngine** | Spearman multi-lag, CAR event study, BH-FDR |
| **Allocation** | Konstrain tepat 100% diuji |
| **Persona** | 5 profil, asimetri loss aversion, rationale terstruktur |
| **Normalizer** | SHA-256, deteksi bahasa, cut-off UTC non-lookahead |
| **Schema** | 14 tabel, migrasi idempoten (`_migrate` aman diulang) |

---

# Urutan Pengerjaan yang Disarankan

Urutan mengikuti **ketergantungan data**, bukan tingkat keparahan. Tidak ada
gunanya memperbaiki cap confidence kalau belum ada satu pun `impact` yang lahir.

## Fase 1 — Sambungkan pipa (tidak ada nilai sebelum ini)
1. **K-6** — panggil `seed_asset_master()` + `seed_aliases()` saat init → `/api/universe` hidup
2. **K-5** — perintah `prices` di CLI: `PriceCollector` → `save_price()`
3. **K-1** — `run_pipeline()`: `raw_articles → normalize → route → save_article(s)`
4. **K-1** — lanjutkan sampai `impacts` + `daily_sentiment`

## Fase 2 — Bikin hasilnya bisa dipercaya
5. **K-4** — `predict_probs()` melempar bila belum `fit`; `scikit-learn` ke requirements
6. **T-7** — `pyarrow` + `openpyxl` ke requirements (CI merah)
7. **T-4** — satu sumber kebenaran: baca `source_registry.yaml`, hapus hardcode
8. **S-4** — 1 test integrasi end-to-end dari `raw_articles` ke `impacts`

## Fase 3 — Lengkapi FR
9. **T-1** — OLS HAC + Granger + `statsmodels`
10. **T-5** — tabel kebijakan cap di YAML, hapus angka ajaib
11. **S-1** — ganti angka hardcoded dengan query DB
12. **S-2** — persist `persona_views` & `alloc_suggestions`
13. **T-2** — CLI lengkap (FR-14)
14. **T-3** — tabel `source_health` + alert

## Fase 4 — ML & penyempurnaan
15. **K-3** — FinBERT (`model/xau/src/`) — **hanya XAU**
16. **T-6** — near-duplicate detection
17. **S-5** — isi `news_horizon` dari router
18. **S-6** — ingest CSV/JSON/manual
19. **S-3** — pakai `ParquetStore` + `ReportExporter`, beri test

> `model/fomc/` tidak masuk urutan pengerjaan. Tetap kosong sampai ada
> keputusan terpisah.

---

## Catatan Metodologi

Semua temuan v2 diverifikasi dengan eksekusi, bukan pembacaan kode saja:

- `grep` pemanggil untuk 10 komponen → 9 di antaranya **0 pemanggil**
- `sqlite3` hitung baris 14 tabel `data/finews.db` → hanya `raw_articles` berisi (38)
- `Database("data/finews.db").get_active_universe()` → `[]`
- `BaselineTfidfSentiment().predict_probs([...])` → prior konstan tanpa error
- `re.findall(r"INSERT INTO (\w+)")` pada `db.py` → 11/14 tabel
- `import pyarrow|openpyxl|sklearn|statsmodels` → dicek satu per satu
- `pytest` → 62 passed, 11 file
- `git check-ignore data/finews.db` → ter-ignore (aman, tidak akan ter-commit)

Satu koreksi metodologi dari v1: pemetaan tabel→method lewat pola nama
`save_<tabel>` **salah** — `save_stat` menyembunyikan `stat_results`, dan
`seed_asset_master`/`seed_aliases` menyembunyikan `asset_master`/`asset_aliases`.
v1 melaporkan 4/14 padahal sebenarnya 11/14. v2 memakai `INSERT INTO` langsung.

Yang **tidak** diverifikasi: klaim akurasi router 95–98% (butuh sampel lebih
besar), dan perilaku API dengan data berisi (belum ada data untuk dibaca).

## Risiko yang perlu diketahui

1. **Yahoo chart API tidak resmi** — bisa diblokir kapan saja; `fetch_prices`
   akan melempar error (perilaku benar, tapi berarti harga berhenti).
2. **Marketaux free tier** 100 req/hari; HTTP 500 = kuota habis, bukan bug.
3. **AlphaVantage** `NEWS_SENTIMENT` premium — tidak berguna di kunci gratis.
4. **Relevansi kata kunci** masih filter kasar, bukan klasifikasi. Berita ambigu
   bisa lolos atau terbuang.
5. **`data/finews.db` tidak di-commit** (benar secara keamanan), jadi setiap
   clone mulai dari nol dan harus menjalankan ingest sendiri.
