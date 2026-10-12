# ARCHITECTURE — Financial News Sentiment & Market Association System

> Status: Draft v0.8-p3 · GUI FastAPI+Vanilla+ECharts · murni 3 (XAU/RATE_UST/SPX) · tanpa LLM/RAG/agent · Terkait: `PRD.md`, `DESIGN.md`, `SCHEMA.md`, `RULES.md`
> Prinsip utama: **statistik dihitung oleh kode; model hanya membaca teks.**

## 1. Gambaran Umum

```
 ┌───────────────┐   ┌────────────────┐
 │ Berita        │   │ Data harga     │
 │ (ID scraper,  │   │ yfinance       │
 │ EN API/RSS)   │   │ (=F, ^, -USD, X) │
 └──────┬────────┘   └───────┬────────┘
        ▼                    │
 ┌───────────────┐           │
 │ Normalize +   │           │
 │ Dedupe + Tag  │ ◀── source_registry / asset_master
 │ + Time-align  │           │
 └──────┬────────┘           │
        ▼                    │
 ┌───────────────┐           │
 │ Sentiment     │ Gold: TF-IDF+LR → FinBERT; FOMC: TF-IDF+LR → FOMC-RoBERTa
 │               │ (Track A ID mati 2026-10-11; 1 track EN aktif)
 └──────┬────────┘           │
        ▼                    │
 ┌───────────────┐           │
 │ Target impact │ explicit / macro_factor (impact graph)
 │ + Confidence  │           │
 └──────┬────────┘           │
        ▼                    ▼
 ┌─────────────────────────────────┐
 │ Storage (PostgreSQL/SQLite +    │
 │ Parquet)                        │
 └──────────────┬──────────────────┘
                ▼
 ┌───────────────┐
 │ Stat analysis │
 │ (kode)        │
 └──────┬────────┘
        ▼
        Dashboard / CLI / Report
 (seluruh pipeline dijadwalkan: cron → Prefect/Airflow)
```

## 2. Lapisan

| Lapisan | Fungsi | Teknologi | Owner |
|---|---|---|
| Pengumpulan | Ambil berita & harga (B1,B9) | Dataset lokal gold+FOMC, RSS Fed/EIA/Kitco, yfinance 3 supervised (`GC=F`,`^TNX`,`^GSPC`) | Backend |
| Pemrosesan teks | Bersih, dedupe, tag routing + kamus (B3), time-align cut-off UTC (B4) | Python, sentence-transformers, registry + impact graph | Backend |
| Model sentimen | Probabilitas 3 kelas (M1-M5) | TF-IDF+LR, FinBERT (gold), FOMC-RoBERTa (FOMC), klasifier tema | ML |
| Penentuan target | `TargetImpact` writer + validator (B5), kalibrasi terapan (M6-M7) | Rule + impact graph, bobot di config | Backend hitung, ML tuning |
| Penyimpanan | 8 tabel SCHEMA (B9), idempotent hash URL+judul | PostgreSQL/SQLite, Parquet | Backend |
| Analisis | Spearman lag, OLS+HAC, Granger, CAR, BH-FDR (B7) | pandas, statsmodels, scipy | Backend |
| Penyajian | GUI Web (FastAPI REST JSON + Vanilla JS + ECharts offline), TUI Rich Bloomberg-style, dan CLI report snapshot HTML beku (B9) | FastAPI, Uvicorn, Vanilla HTML/CSS/JS, ECharts offline, Rich, Typer | Backend |
| Orkestrasi | cron → Prefect/Airflow, log source_health | cron | Backend |

## 3. Tahap Pipeline

1. **Collect** — tulis ke `raw_articles` apa adanya (idempotent; kunci = hash URL+judul).
2. **Normalize** — bersihkan HTML/iklan, unicode, tanggal → UTC, deteksi bahasa.
3. **Dedupe** — exact hash + near-duplicate (cosine embedding ≥ ambang konfigurasi).
4. **Tag** — tentukan target:
   - **Routing** dari `source_registry` (berita diambil karena query/feed milik target X),
   - **Kamus kata kunci per target** (tanpa NER emiten; emiten dicoret MVP),
   - **Makro** → dirutekan ke semua 3 target.
5. **Time-align** — `effective_trading_date` per bursa; berita setelah tutup → hari bursa berikutnya (timezone-aware).
6. **Sentiment** — lihat `DESIGN.md` §3.
7. **Impact** — `direction` per target; `basis` ∈ {explicit, macro_factor} (sector_inferred dicoret MVP).
8. **Confidence** — dihitung kode deterministik, dikalibrasi.
9. **Aggregate** — skor harian per target (hari tanpa berita = `NaN`).
10. **Analyze** — statistik (lihat `DESIGN.md` §6) → `stat_results`.
11. **Serve** — CLI `report` tulis JSON beku → embed ke satu `report.html` (nol server, nol build, buka offline).

## 4. Sumber Data & Source Registry

`data/source_registry.yaml` memetakan target → sumber & kata kunci. Menambah target = menambah satu entri.

```yaml
version: 2026-10-12-core3   # UNIVERSE INTI: 3 target; tambah/coret = bump version
macro:                     # dirutekan ke 3 target inti
  keywords: [fed, fomc, inflation, cpi, pce, jobs report, payrolls, tariff, rate cut, rate hike, war]
  feeds:
    - {name: fed_press, type: rss, lang: en}     # URL diverifikasi saat implementasi
    - {name: gdelt, type: api, lang: multi}
targets:
  XAU:      {price: "GC=F",    keywords: [gold, bullion, safe haven, real yields, emas], feeds: [kitco_rss, wgc]}
  RATE_UST: {price: "^TNX",    keywords: [treasury yield, 10-year, fed funds, fomc], feeds: [fed_press], note: "yield = ^TNX/10"}
  SPX:      {price: "^GSPC",   keywords: [s&p 500, wall street, earnings, jobs, cpi], api: finnhub_marketaux}
# DICORET MVP: XAG (duplikat XAU), NDX/DJI (duplikat SPX), EUR/USD, emiten individual, uranium/lithium/nikel, SUN/SBSN/ORI/SBR + corporate/EM bonds.
```

### Sumber berita (catatan penting)

| Sumber | Dipakai untuk | Catatan |
|---|---|---|
| `news-watch` (PyPI) | Berita ID berbasis kata kunci & tanggal | Mendukung Bisnis Indonesia, CNBC Indonesia, Kontan (cek daftar terbaru) |
| Scraper sendiri | Portal ID lain | Patuhi robots.txt/ToS |
| Finnhub | Berita EN per perusahaan/pasar | Free tier terbatas; sebagian sentimen berbayar — cek batas terbaru |
| Marketaux | Berita EN multi-bahasa + tag ticker | Kuota harian kecil — cek |
| Alpha Vantage News | Berita + sentimen vendor | Kuota sangat kecil — cek |
| RSS lembaga (Fed, BLS, EIA, Kitco, CoinDesk, dll.) | Makro & komoditas | URL feed bisa berubah — verifikasi |
| GDELT | Makro/geopolitik, cakupan luas | Kualitas teks bervariasi |
| `yfinance` `Ticker.news` | Tambahan saja | Hanya berita terbaru, tanpa riwayat → simpan harian sendiri |
| `id_newspapers_2018` | Pretraining/eksperimen | Domain umum, 2018 saja |

**Karena riwayat API gratis pendek, kolektor harian wajib berjalan sedini mungkin.**

## 5. Orkestrasi

- Mulai dengan **cron/Prefect** untuk jadwal harian (collect → process → score → aggregate → analyze).

## 6. Struktur Repo

```
.
├── context/                  # spesifikasi inti (PRD, ARCHITECTURE, DESIGN, RULES, SCHEMA)
├── dataset/                  # gold_sinha/ (10.570 human) + fomc/ (48 xlsx human); detail `dataset/README.md`
├── research/                 # katalog riset & PDF 11 paper primer/pendukung
├── data/
│   ├── source_registry.yaml
│   ├── impact_graph.yaml
│   ├── alloc_profiles.yaml   # baseline & batas per profil
│   ├── alloc_map.yaml        # kelas aset ← sumber skor
│   ├── personas.yaml         # parameter 5 persona
│   ├── universe/asset_master.csv (INTI 3 baris aktif, version 2026-10-12-core3)
│   ├── labeled/              # arsip (manual 400-600 MATI; label dari dataset/gold_sinha + dataset/fomc)
│   └── raw/ processed/       # Parquet time-series
├── model/                    # ML Engineer track (M1–M7)
│   ├── notebooks/            # EDA, pelatihan, ablation TF-IDF vs transformer, validasi temporal
│   ├── weights/              # bobot model beku (.pkl, safetensors, ECE calibrator)
│   └── evaluation/           # evaluasi F1 macro, ECE, bootstrap CI, McNemar
├── backend/                  # Backend Engineer track (B1–B9)
│   ├── src/
│   │   ├── collect/          # scrapers RSS/API + yfinance 3 target (GC=F, ^TNX, ^GSPC)
│   │   ├── normalize/        # clean, dedupe, cut-off 00:00 UTC, kalender bursa
│   │   ├── tagging/          # routing registry + impact_graph (tanpa NER)
│   │   ├── aggregate/        # DailySentiment mean (hari kosong = NULL)
│   │   ├── alloc/            # Allocation Tilt engine (100% constrain)
│   │   ├── persona/          # Persona POV engine (5 persona)
│   │   ├── stats/            # Spearman, OLS HAC, Granger, CAR event study
│   │   ├── store/            # SQLite + Parquet repository
│   │   ├── report/           # JSON payload exporter & HTML report builder
│   │   └── serve/            # FastAPI REST endpoints (/api/...) & static file mount
│   └── tests/                # unit tests pipeline deterministik
├── frontend/                 # Lapisan antarmuka pengguna
│   ├── GUI/                  # Visualisasi FR-15 web statis (zero-server, offline ECharts)
│   │   ├── src/css/          # styling tema Dark (#FF7517, #3E3939, #2C2727, #F6F4F4)
│   │   ├── src/js/           # logika render ECharts offline
│   │   └── templates/        # template HTML statis single-file
│   └── TUI/                  # Terminal UI interaktif (Bloomberg-style, Rich/Textual)
│       └── src/              # layout, keymaps, theme tokens (#FF7517, #3E3939, #2C2727, #F6F4F4)
└── outputs/                  # artefak beku report.html, log, plot
```

## 7. Keputusan Desain

| # | Keputusan | Alasan |
|---|---|---|
| D1 | Statistik oleh kode deterministik | Deterministik & reproducible |
| D2 | Satu track EN, murni 3 supervised (XAU/RATE_UST/SPX) | Label human cover 3; 7 dicoret; klaim jujur, hindari 10-way |
| D3 | ~~Fusion late~~ — MATI (Track A hapus); ablation langsung TF-IDF+LR vs transformer | Satu track EN, data human cukup |
| D4 | Source routing berbasis registry (data, bukan kode) | Mudah diaudit & ditambah |
| D5 | Makro dirutekan ke semua target | Dampak lintas aset tidak hilang |
| D6 | Confidence dihitung kode + dikalibrasi | Konsisten, anti-overconfidence |
| D7 | Hari tanpa berita = `NaN` | Hindari bias nol |
| D8 | Simpan versi model/universe/skema | Reproducibility |
| D9 | Komponen dipakai hanya jika mengalahkan pembanding sederhana | Hindari kompleksitas tak perlu |

## 8. Error Handling & Observability

- Retry + backoff untuk HTTP/API; scraper gagal tidak menghentikan pipeline (catat `source_health`).
- Logging terstruktur per `article_id`; metrik: jumlah berita/hari/sumber, duplikasi, latensi & biaya per tahap, tingkat penolakan validator.
- Alert bila sumber tidak menghasilkan berita > N hari.

## 9. Keamanan & Kepatuhan

- API key via `.env` (tidak di repo).
- Hormati ToS/robots.txt; jika lisensi melarang, simpan metadata + skor + ringkasan.
- Semua output memuat: **bukan nasihat investasi**.

## 10. Modul Tambahan v0.3

```
 TargetImpact (+news_horizon)
        │
        ├──▶ alloc/  : skor per kelas aset → tilt → AllocationSuggestion
        └──▶ persona/: skor × parameter persona → stance BUY/HOLD/SELL → PersonaView
                         │
                         └──▶ explainer (template deterministik; tidak mengubah keputusan)
```

- **alloc/**: membaca `alloc_profiles.yaml` (baseline, min, max, λ, batas pergeseran) dan `alloc_map.yaml` (kelas aset ← sumber skor). Keluaran: alokasi baru (total 100%) + delta + alasan.
- **persona/**: membaca `personas.yaml`; murni fungsi deterministik. Penjelas teks pakai template deterministik; **stance dihitung kode**.
- Keduanya mengonsumsi `TargetImpact` dan `DailySentiment` yang sama; tidak ada model baru yang perlu dilatih.
- Data tambahan: yield SBN/NAV reksadana sumber TBD → lampiran riset, bukan target MVP. ETF acuan = SPX (terkunci).
- Keputusan: D10 — alokasi & persona **dihitung kode deterministik** agar reproducible; D11 — tilt terbatas relatif baseline.
