# Graph Report - .  (2026-10-21)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1423 nodes · 2670 edges · 94 communities (69 shown, 25 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 167 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `013e20a3`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- .compute_ols_hac
- schema.py
- Pipeline
- NewsHorizon
- BaselineTfidfSentiment
- DESIGN — Model, Scoring, Statistik & Antarmuka
- app.js
- PriceRecord
- DailyQuota
- ApiRegistry
- ApiStatus
- NearDuplicateDetector
- .get_connection
- test_news_api.py
- Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro
- main
- ModelRouter
- test_source_registry.py
- Dataset Card for Sentiment Analysis of Commodity News (Gold)
- cli.py
- ReportExporter
- Database
- adapters.py
- PRD — Financial News Sentiment & Market Association System
- RULES — Aturan Wajib Proyek
- Upgrade UI FInews
- test_pipeline_integration.py
- test_source_health.py
- DailySentiment
- EulerpoolAdapter
- FinnhubAdapter
- test_api_no_hardcoded.py
- Jalur Data — K-3 → A → C → B
- GUI THEME — Claude × Bloomberg
- test_router_config.py
- AUDIT v4 — Database, Backend & ML
- ApiError
- test_persistence.py
- ARCHITECTURE — Financial News Sentiment & Market Association System
- FinNews: Financial News Sentiment & Market Association System
- date
- ParquetStore
- 01_baseline_exploration.py
- SCHEMA — Data Contracts
- NewsItem
- AGENTS.md — Panduan untuk AI Agent Kolaborator
- NewsAPIAdapter
- Model Router: Cascade Routing ke Model Spesialis
- train_baseline.py
- MarketauxAdapter
- ._parse
- FeedStatus
- cmd_report
- .get_active_universe
- .seed_aliases
- fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX)
- xau/ — Track FinBERT-EMAS (target XAU)
- .init_schema
- .save_label
- dataset/ — Katalog Data
- Theme & Splash — Bloomberg 70% × Claude 30%
- Model Research Notebooks
- model/ — ML Research & Inference Pipeline (M1–M7)
- research/ — Ringkasan Paper Terkait
- .__init__
- db
- frontend/GUI/ — Static ECharts HTML Dashboard (FR-15)
- README.md
- __init__.py
- .__init__
- .get_alloc_suggestions
- .is_valid_target
- .latest_source_health
- .query_stats
- .save_alloc_suggestion
- .save_labels
- .save_price
- .save_raw_articles
- .save_stat
- __init__.py
- __init__.py
- README.md
- README.md
- theme.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- __init__.py
- finews

## God Nodes (most connected - your core abstractions)
1. `Database` - 119 edges
2. `Pipeline` - 39 edges
3. `ApiError` - 37 edges
4. `TargetImpact` - 36 edges
5. `NewsItem` - 33 edges
6. `Article` - 33 edges
7. `TargetRouter` - 31 edges
8. `BaselineTfidfSentiment` - 30 edges
9. `EulerpoolAdapter` - 29 edges
10. `ApiStatus` - 28 edges

## Surprising Connections (you probably didn't know these)
- `PipelineError` --uses--> `BaselineTfidfSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/common/baseline.py
- `PipelineStats` --uses--> `BaselineTfidfSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/common/baseline.py
- `Pipeline` --uses--> `BaselineTfidfSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/common/baseline.py
- `BaselineTfidfSentiment` --uses--> `Tone`  [INFERRED]
  model/common/baseline.py → backend/src/schema.py
- `ModelNotFittedError` --uses--> `Tone`  [INFERRED]
  model/common/baseline.py → backend/src/schema.py

## Import Cycles
- None detected.

## Communities (94 total, 25 thin omitted)

### Community 0 - ".compute_ols_hac"
Cohesion: 0.06
Nodes (55): StatResult, Any, DataFrame, date, Deterministic statistical engine for sentiment-market association., Frame bersih: terurut tanggal, kolom `return`, tanpa baris kosong.          Sent, Aturan bandwidth Newey-West: floor(4 * (n/100) ** (2/9))., Regresi OLS `return ~ sentiment` dengan galat standar Newey-West (HAC). (+47 more)

### Community 1 - "schema.py"
Cohesion: 0.06
Nodes (50): AssetClass, Basis, Direction, EvidenceSpan, Enum, str, Data contracts and validation models (SCHEMA v0.6.0)., TargetImpact (+42 more)

### Community 2 - "Pipeline"
Cohesion: 0.08
Nodes (38): ArticleCleaner, date, datetime, Normalization, deduplication, language detection, and time-alignment., Prepares raw incoming articles for pipeline consumption., Cleans whitespace, HTML tags, and non-printable characters., Generates sha256(norm(title)+norm(body))[:16] per SCHEMA., Simple heuristic language detector for ID vs EN. (+30 more)

### Community 3 - "NewsHorizon"
Cohesion: 0.06
Nodes (38): AllocationEngine, Path, Deterministic Allocation Tilt engine satisfying strict 100% sum constraint., Computes relative portfolio tilt adjustments from asset scores., Derives scores for 6 allocation classes using alloc_map.yaml.         Score tupl, Calculates constrained allocation tilt for a specific profile.         Strictly, Allocation Tilt simulation engine., PersonaEngine (+30 more)

### Community 4 - "BaselineTfidfSentiment"
Cohesion: 0.06
Nodes (32): ABC, ArticleSentiment, ModelProbs, Tests for baseline ML model and evaluation metrics., Model tanpa fit()/load() harus melempar, bukan mengarang prior.      Sebelum per, fit() pada data kecil harus menghasilkan prediksi valid., Model nyata harus memberi sinyal berbeda untuk teks bullish vs bearish., test_fit_membuat_model_siap() (+24 more)

### Community 5 - "DESIGN — Model, Scoring, Statistik & Antarmuka"
Cohesion: 0.04
Nodes (47): 10. Keterbatasan, 11.1 Kelas aset, 11.2 Skor per kelas (`alloc_map.yaml`), 11.3 Rumus, 11.4 Preset profil (contoh, bisa diubah; total wajib 100%), 11.5 Output, 11. Allocation Tilt, 12.1 Persona awal (`personas.yaml`) (+39 more)

### Community 6 - "app.js"
Cohesion: 0.11
Nodes (46): api(), applyNewsFilter(), bindControls(), bindPersonaButtons(), bindTabs(), demoImpacts(), demoQuality(), demoSeries() (+38 more)

### Community 7 - "PriceRecord"
Cohesion: 0.07
Nodes (33): Market data and news collectors., FetchResult, PriceCollector, PriceFetchError, date, Path, RuntimeError, Price data collector for the 3 core locked assets (XAU, RATE_UST, SPX).  Sumber (+25 more)

### Community 8 - "DailyQuota"
Cohesion: 0.08
Nodes (33): DailyQuota, Connection, Path, RuntimeError, QuotaExceeded, QuotaStatus, Penjaga kuota request harian — untuk sumber dengan batas 10–100 req/hari.  Menga, Baca pemakaian hari ini tanpa menambah apa pun. (+25 more)

### Community 9 - "ApiRegistry"
Cohesion: 0.09
Nodes (32): datetime, Timestamp UTC timezone-aware — dipakai sebagai fetched_at., Konversi ke kontrak `RawArticle` (SCHEMA)., utcnow(), ApiRegistry, identify_apis(), Nama penyedia yang env var-nya kosong., Laporan kesehatan semua penyedia.          `probe=False` hanya memeriksa keberad (+24 more)

### Community 10 - "ApiStatus"
Cohesion: 0.11
Nodes (22): Adapter Alpha Vantage NEWS_SENTIMENT.  Endpoint: GET /query?function=NEWS_SENTIM, ApiStatus, HealthReport, Any, Enum, str, Primitif bersama untuk seluruh adapter news API., Hasil identifikasi satu penyedia API. (+14 more)

### Community 11 - "NearDuplicateDetector"
Cohesion: 0.09
Nodes (31): _compose(), NearDuplicateDetector, FR-2 / T-6: deteksi artikel near-duplicate.  Dedup yang ada sebelumnya hanya *ex, Kembalikan daftar artikel dengan `duplicate_of` terisi bila perlu.          `his, Teks pembanding: judul diberi bobot lebih dengan cara diulang.      Badan berita, Menandai artikel yang mirip dengan artikel lain via `duplicate_of`., Matriks cosine similarity antar teks. Mengembalikan None bila kosong., _article() (+23 more)

### Community 12 - ".get_connection"
Cohesion: 0.06
Nodes (12): Simpan PersonaView ke tabel `persona_views`.          NFR reproducibility: hasil, Baca kembali persona_views yang tersimpan (untuk audit)., Sumber yang SEDANG gagal `threshold` kali berturut-turut.          Hanya keadaan, Stores a TargetImpact record., Stores daily aggregate sentiment for an asset., Stores a raw (unnormalized) article. Returns raw_id.          Deduplikasi memaka, Returns raw articles, terbaru dulu., Stores a normalized article. (+4 more)

### Community 13 - "test_news_api.py"
Cohesion: 0.10
Nodes (27): count_hits(), _load_registry(), matches_target(), _pattern(), Path, Kata kunci relevansi target — dibaca dari `data/source_registry.yaml`.  Registry, Jumlah kata kunci berbeda yang cocok di teks., Skor relevansi: 2x kata kunci target + 1x kata kunci makro.      Skor 0 berarti (+19 more)

### Community 14 - "Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro"
Cohesion: 0.06
Nodes (31): 1.1 Masalah & Problem Statement, 1.2 Objektif, Metrik Domain, dan Metrik Teknis, 1.3 Uji Kecocokan Solusi (Component Necessity Test), 1. Problem Framing, 2.1 Tujuan Sistem, 2.2 Prinsip Desain, 2.3 Cakupan 3 Target Makro Terkunci (Murni 3 v2026-10-11-p3), 2. Deskripsi Sistem (+23 more)

### Community 15 - "main"
Cohesion: 0.10
Nodes (29): main(), Dengan data minim, `stats` harus berhenti dengan pesan jelas (exit 0)., DB kosong: lewati tabel kosong, jangan menulis file palsu., test_export_on_empty_db_does_not_crash(), test_stats_reports_insufficient_pairs_without_crashing(), test_status_runs(), _count(), Path (+21 more)

### Community 16 - "ModelRouter"
Cohesion: 0.10
Nodes (24): ModelRouter, Path, Two-stage cascade router: news text -> specialist model id.  Tahap 1: petunjuk s, Lowercase token tanpa stopword. Dipakai builder dan router., Routes an article to the specialist model that should score it., Rata-rata z dan jumlah bukti kuat per domain., Returns (model_ids, reason, score). reason: source|keyword|log_odds|fallback., tokens() (+16 more)

### Community 17 - "test_source_registry.py"
Cohesion: 0.08
Nodes (22): _load_feeds(), Path, Baca `targets.<ID>.feeds` dari registry.      Hanya entri ber-`type: rss` yang d, T-4 / FR-3: registry YAML adalah satu-satunya sumber kebenaran.  Sebelum perbaik, Entri non-RSS (mis. deklarasi API) tidak boleh masuk daftar feed., Registry hilang: program tetap hidup, tetapi jujur soal sumbernya., Cadangan harus jauh lebih kecil dari registry asli.      Kalau cadangan sama pan, Regresi: pindah ke YAML tidak boleh mengurangi cakupan routing.      Daftar lama (+14 more)

### Community 18 - "Dataset Card for Sentiment Analysis of Commodity News (Gold)"
Cohesion: 0.09
Nodes (22): Acknowledgements, Bias, Risks, and Limitations, Citation, Content, Context, Curation Rationale, Data Collection and Processing, Data Fields (+14 more)

### Community 19 - "cli.py"
Cohesion: 0.16
Nodes (21): build_parser(), cmd_aggregate(), cmd_clean(), cmd_export(), cmd_pipeline(), cmd_prices(), cmd_score(), cmd_seed() (+13 more)

### Community 20 - "ReportExporter"
Cohesion: 0.10
Nodes (17): Any, Path, Generates static HTML and JSON analytical reports into outputs/., Exports system analytical snapshots and statistics., Exports analytical JSON snapshot., Renders self-contained static HTML report for the 3 core targets., ReportExporter, Report export utilities. (+9 more)

### Community 21 - "Database"
Cohesion: 0.19
Nodes (21): Database, Manages SQLite connections and queries for FInews., db(), _article(), db(), Test untuk CRUD tabel berita (K-3) dan kolektor RSS., _raw(), test_get_missing_article_returns_none() (+13 more)

### Community 22 - "adapters.py"
Cohesion: 0.20
Nodes (18): fomc_stance(), fomc_to_raw(), fomc_tone(), _gold_parse_date(), gold_to_raw(), gold_tone(), DataFrame, datetime (+10 more)

### Community 23 - "PRD — Financial News Sentiment & Market Association System"
Cohesion: 0.10
Nodes (20): 10. Sumber Data (ringkas; detail di `ARCHITECTURE.md` §4), 11. Fase, 12. Risiko, 13. Open Questions, 14.1 Allocation Tilt, 14.2 Persona POV (5 persona), 14.3 Catatan Penting, 14. Fitur Tambahan (v0.3) (+12 more)

### Community 24 - "RULES — Aturan Wajib Proyek"
Cohesion: 0.10
Nodes (20): 10. Untuk AI Assistant yang Mengerjakan Repo Ini, 11.1 Aturan Frontend (GUI Web & TUI), 11. Aturan Allocation Tilt & Persona POV (v0.3), 1.1 Definisi, 1.2 `basis` dan batas confidence, 1.3 Evidence & rationale, 1.4 Target, 1.5 Disclaimer (+12 more)

### Community 25 - "Upgrade UI FInews"
Cohesion: 0.10
Nodes (20): 1. Tujuan, 2. Kondisi UI Saat Ini, 3.1 Adaptasi Splash Screen yang Sudah Ada, 3. Struktur Halaman yang Direkomendasikan, 4. Prioritas Upgrade, 5. Perubahan Kontrak Minimum, 6. Urutan Implementasi, 7. Yang Sengaja Tidak Dibuat (+12 more)

### Community 26 - "test_pipeline_integration.py"
Cohesion: 0.16
Nodes (19): _count(), db_path(), _iso(), datetime, Path, Test integrasi end-to-end: raw_articles -> articles -> impacts -> daily_sentimen, Menjalankan dua kali tidak boleh menggandakan baris., --dry-run menghitung tapi tidak menyentuh database. (+11 more)

### Community 27 - "test_source_health.py"
Cohesion: 0.10
Nodes (12): db(), Tests for T-3: riwayat kesehatan sumber & alert (FR-18).  Yang diuji bukan sekad, Detail sangat panjang tidak boleh menggembungkan tabel tanpa batas., Satu-dua kegagalan belum boleh memicu alert., Setelah sumber pulih, alert harus berhenti -- bukan menyala selamanya., `no_key` adalah pilihan konfigurasi, bukan sumber yang mati., Pemeriksaan dalam detik yang sama tidak boleh menghasilkan baris ganda.      `ch, test_alert_clears_after_recovery() (+4 more)

### Community 28 - "DailySentiment"
Cohesion: 0.14
Nodes (14): DailyAggregator, date, Aggregates article impacts into daily sentiment series., Computes daily mean and weighted sentiment per target., Aggregates impacts for a single asset on a given trading date.         Strict in, Aggregates batch of impacts, explicitly creating empty records         with scor, Daily sentiment aggregation across assets., DailySentiment (+6 more)

### Community 29 - "EulerpoolAdapter"
Cohesion: 0.20
Nodes (10): EulerpoolAdapter, Any, datetime, Satu panggilan HTTP. Memesan kuota lebih dulu bila dijaga.          `limit` di-c, `datetime` dari Eulerpool berupa epoch detik (int)., Tolak berita lebih tua dari MAX_AGE_DAYS atau bertanggal masa depan., Cek kunci dengan satu request minimum (limit=1)., Tarik berita relevan untuk satu target.          Biaya kuota: **1 request**, ber (+2 more)

### Community 30 - "FinnhubAdapter"
Cohesion: 0.16
Nodes (10): FinnhubAdapter, Any, Tarik berita relevan untuk satu target.          Menggabungkan beberapa kategori, ApiSpec, Path, Metadata satu penyedia API., Muat .env bila ada. Tidak melempar bila file tidak ditemukan., _specs() (+2 more)

### Community 31 - "test_api_no_hardcoded.py"
Cohesion: 0.14
Nodes (16): Tests for S-1: endpoint API tidak boleh menyajikan angka karangan.  Sebelum perb, Parameter eksplisit tetap boleh menimpa DB (untuk eksplorasi)., Skor dari DB harus memengaruhi hasil, bukan konstanta., Aset tanpa data harus ditandai `tanpa_data`, bukan diberi angka karangan., Regresi: 0.25/0.70 tidak boleh muncul lagi sebagai skor XAU., Batas keras RULES: total alokasi harus tetap 100%., Tanpa dampak tercatat, endpoint harus 404 -- bukan mengarang skor., Bila dampak ada, angka dari DB yang dipakai. (+8 more)

### Community 32 - "Jalur Data — K-3 → A → C → B"
Cohesion: 0.12
Nodes (15): Batasan yang perlu diketahui, Feed terverifikasi hidup, Feed yang dibuang (jangan dipakai lagi), Identifikasi API, Jalur A — Harga, Jalur B — Berita via RSS, Jalur C — Berita via API, Jalur Data — K-3 → A → C → B (+7 more)

### Community 33 - "GUI THEME — Claude × Bloomberg"
Cohesion: 0.12
Nodes (15): 10. Tipografi (ringkas; versi font gratis padanan), 11. CSS Variables (siap salin), 12. Konfigurasi Streamlit (jika dipakai; cek dukungan font kustom pada versi yang dipakai), 13. Daftar Periksa Implementasi, 1. Konsep, 2. Warna Inti (dari spesifikasi), 3. Token Turunan — Sisi Terang, 4. Token Turunan — Sisi Gelap (Technical Surface) (+7 more)

### Community 34 - "test_router_config.py"
Cohesion: 0.17
Nodes (14): Tests for T-5: ambang & kalibrasi router berasal dari YAML, bukan kode.  Alasan, Router yang membaca config dari tmp_path (bukan data/ asli)., Nilai bawaan harus identik dengan angka yang dulu ditanam di kode.      Kalau be, Plafon keyakinan makro tidak boleh terlampaui berapa pun bobotnya., Menaikkan ambang harus bisa memaksa arah menjadi NETRAL., YAML rusak tidak boleh membuat router mati total., _router(), test_broken_yaml_falls_back_to_defaults() (+6 more)

### Community 35 - "AUDIT v4 — Database, Backend & ML"
Cohesion: 0.13
Nodes (14): 1. FR-6 / K-3 · FinBERT XAU belum ada — **P0, satu-satunya yang kosong**, 2. FR-2 · near-duplicate tidak terbukti bekerja — **P0, biaya kecil**, 3. FR-1 · ingest CSV/JSON/manual belum ada — **P0, parsial**, 4. FR-20 · tabel `alloc_profiles` mati — **P1, kosmetik arsitektur**, AUDIT v4 — Database, Backend & ML, Cakupan Test, Catatan Metodologi, Kenapa v4 ini ada (+6 more)

### Community 36 - "ApiError"
Cohesion: 0.18
Nodes (9): ApiError, Any, GET JSON dengan retry. Melempar `ApiError` setelah percobaan habis.          `he, GET teks mentah (untuk RSS/XML)., Kegagalan HTTP yang sudah diklasifikasi., test_api_error_carries_status(), test_client_masks_secrets_in_params(), Exception (+1 more)

### Community 37 - "test_persistence.py"
Cohesion: 0.14
Nodes (10): env(), Tests for S-2: persona_views & alloc_suggestions harus dipersistensi.  NFR repro, Audit butuh jejak: versi parameter dan waktu pembuatan., Yang disimpan harus sama dengan yang dikirim ke klien., Pemanggilan ulang harus menimpa, bukan menumpuk baris kembar., Tidak ada dampak -> tidak ada yang disimpan (jangan simpan karangan)., test_persisted_persona_matches_response(), test_persisted_rows_carry_provenance() (+2 more)

### Community 38 - "ARCHITECTURE — Financial News Sentiment & Market Association System"
Cohesion: 0.14
Nodes (13): 10. Kontrak Penyajian, 11. Modul Tambahan v0.3, 1. Gambaran Umum, 2. Lapisan, 3. Tahap Pipeline, 4. Sumber Data & Source Registry, 5. Orkestrasi, 6. Struktur Repo (+5 more)

### Community 39 - "FinNews: Financial News Sentiment & Market Association System"
Cohesion: 0.15
Nodes (12): 1. Prasyarat & Instalasi, 2. Menjalankan Unit Test, 3. Eksplorasi Baseline Model (ML Offline), 4. Menjalankan Server API Backend, 🏛️ Arsitektur Sistem (3-Tier Layer), 🔒 Aturan Desain & Integritas Kuantitatif, FinNews: Financial News Sentiment & Market Association System, 🎯 Murni 3 Supervised (`XAU` / `RATE_UST` / `SPX`) (+4 more)

### Community 40 - "date"
Cohesion: 0.17
Nodes (6): date, Retrieves joint sentiment and price series for a target., Stores one article→target mapping., Bulk insert mappings untuk satu artikel. Returns jumlah baris., Queries daily sentiment records between dates., Queries price records between dates.

### Community 41 - "ParquetStore"
Cohesion: 0.20
Nodes (8): ParquetStore, Any, DataFrame, Path, Parquet storage helpers for bulk dumps and training datasets., Manages Parquet writes and reads for processed time series., Saves records to a Parquet file., Reads records from a Parquet file.

### Community 42 - "01_baseline_exploration.py"
Cohesion: 0.20
Nodes (10): Tests F1 macro, accuracy, and kappa computation., test_evaluation_metrics(), 01_baseline_exploration.py  Eksplorasi baseline model (M1: TF-IDF + Logistic Reg, Menjalankan pelatihan dan evaluasi baseline sentiment.     Labels: 0 = Negative,, run_experiment(), compute_ece(), evaluate_predictions(), Evaluation metrics for sentiment models: F1 macro, ECE, Cohen's Kappa. (+2 more)

### Community 43 - "SCHEMA — Data Contracts"
Cohesion: 0.17
Nodes (11): 1. Enum, 2. Model Pipeline (Pydantic v2), 3. Output JSON (contoh), 4. Universe (`asset_master`), 5. Source Registry & Impact Graph, 6. Tabel Database (SQL), 7. Invarian (wajib dijaga validator), 8.1 Kontrak Role (+3 more)

### Community 44 - "NewsItem"
Cohesion: 0.33
Nodes (6): AlphaVantageAdapter, Any, NewsItem, Satu berita mentah, belum dinormalisasi (belum punya article_id)., test_alphavantage_without_key_is_not_configured(), test_news_item_to_raw_article()

### Community 45 - "AGENTS.md — Panduan untuk AI Agent Kolaborator"
Cohesion: 0.20
Nodes (9): 1. Mulai dari sini, bukan dari `ls -R`, 2. Peta cepat: di mana apa, 3. Aturan yang tidak boleh dilanggar, 4. Lingkup kerja per peran, 5. Perintah yang sering dipakai, 6. Konvensi commit, 7. Kondisi repository saat ini, 8. Saat ragu (+1 more)

### Community 46 - "NewsAPIAdapter"
Cohesion: 0.20
Nodes (6): NewsAPIAdapter, Protocol, Tarik berita untuk satu target universe., Kontrak setiap adapter penyedia berita., True bila kredensial tersedia., Uji ringan: kunci valid? ada data?

### Community 47 - "Model Router: Cascade Routing ke Model Spesialis"
Cohesion: 0.20
Nodes (9): Arsitektur: dua tahap + fallback, Batasan yang diketahui, Cara menjalankan, Jejak audit, Masalah, Mengapa aturan bukti, bukan rata-rata, Model Router: Cascade Routing ke Model Spesialis, Tahap 1 — sumber dan kata kunci (+1 more)

### Community 48 - "train_baseline.py"
Cohesion: 0.33
Nodes (8): load_split(), main(), _proba_matrix(), Path, Melatih baseline TF-IDF + LR dari dataset gold_sinha (nyata, berlabel).  Dataset, Membaca satu split parquet, mengembalikan (texts, labels)., Melatih dan menyimpan model. Mengembalikan metrik evaluasi., train()

### Community 49 - "MarketauxAdapter"
Cohesion: 0.46
Nodes (3): MarketauxAdapter, Any, test_marketaux_without_key_is_not_configured()

### Community 50 - "._parse"
Cohesion: 0.29
Nodes (6): _clean(), Parse RSS 2.0 atau Atom menjadi list dict mentah., Buang tag HTML dan rapikan spasi., test_rss_parse_atom(), test_rss_parse_invalid_xml_raises(), test_rss_parse_rss20()

### Community 51 - "FeedStatus"
Cohesion: 0.33
Nodes (4): FeedStatus, Uji satu feed tanpa melempar., Kesehatan semua feed (atau hanya milik satu target)., Versi `HealthReport` agar seragam dengan adapter API.

### Community 52 - "cmd_report"
Cohesion: 0.40
Nodes (6): cmd_report(), cmd_status(), _print_stok(), Path, Cetak jumlah baris tiap tabel — untuk memastikan data benar-benar ada., Ekspor outputs/report.html mandiri (RULES.md:144).

### Community 53 - ".get_active_universe"
Cohesion: 0.20
Nodes (3): Dampak satu artikel pada satu aset, atau None bila tidak ada.          Dipakai e, Returns all 3 active core universe assets., Returns real provenance facts for GET /api/meta.          Everything comes from

### Community 54 - ".seed_aliases"
Cohesion: 0.33
Nodes (3): Path, Seeds the 3 core locked assets from asset_master.csv., Seeds asset aliases from aliases.csv.

### Community 55 - "fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX)"
Cohesion: 0.33
Nodes (5): fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX), Kerangka, Kontrak, Tugas track ini (M3, M6), Yang belum ada

### Community 56 - "xau/ — Track FinBERT-EMAS (target XAU)"
Cohesion: 0.33
Nodes (5): Kerangka, Kontrak, Tugas track ini (M2, M6), xau/ — Track FinBERT-EMAS (target XAU), Yang belum ada

### Community 57 - ".init_schema"
Cohesion: 0.40
Nodes (3): Connection, Initializes tables and indexes, lalu migrasi kolom yang menyusul., Menambah kolom baru pada DB lama. Idempoten dan aman diulang.

### Community 58 - ".save_label"
Cohesion: 0.40
Nodes (3): datetime, Catat satu hasil pemeriksaan kesehatan sumber.          Mengembalikan jumlah keg, Stores one human annotation.

### Community 59 - "dataset/ — Katalog Data"
Cohesion: 0.40
Nodes (4): dataset/ — Katalog Data, Dihapus 2026-10-11, Mapping label (beku), Sitasi

### Community 61 - "Theme & Splash — Bloomberg 70% × Claude 30%"
Cohesion: 0.40
Nodes (4): Catatan, Streamlit, Theme & Splash — Bloomberg 70% × Claude 30%, Web biasa

### Community 63 - "Model Research Notebooks"
Cohesion: 0.50
Nodes (3): Model Research Notebooks, Standar Output Artefak:, Struktur Notebook:

### Community 64 - "model/ — ML Research & Inference Pipeline (M1–M7)"
Cohesion: 0.50
Nodes (3): Aturan pembagian, model/ — ML Research & Inference Pipeline (M1–M7), Pemetaan Modul (M1–M7)

### Community 65 - "research/ — Ringkasan Paper Terkait"
Cohesion: 0.50
Nodes (3): 1. Paper Utama & Pendukung (Tersimpan di `research/papers/`), 2. Sintesis untuk Sidang Skripsi / TA, research/ — Ringkasan Paper Terkait

### Community 67 - "db"
Cohesion: 0.67
Nodes (3): db(), Path, test_migration_adds_route_columns()

## Knowledge Gaps
- **235 isolated node(s):** `finews`, `1. Mulai dari sini, bukan dari `ls -R``, `2. Peta cepat: di mana apa`, `3. Aturan yang tidak boleh dilanggar`, `4. Lingkup kerja per peran` (+230 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **25 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `.compute_ols_hac`, `schema.py`, `Pipeline`, `NewsHorizon`, `BaselineTfidfSentiment`, `PriceRecord`, `ApiRegistry`, `.get_connection`, `main`, `cli.py`, `test_pipeline_integration.py`, `test_source_health.py`, `DailySentiment`, `test_api_no_hardcoded.py`, `test_persistence.py`, `date`, `cmd_report`, `.get_active_universe`, `.seed_aliases`, `.init_schema`, `.save_label`, `db`, `.__init__`, `.get_alloc_suggestions`, `.is_valid_target`, `.latest_source_health`, `.query_stats`, `.save_alloc_suggestion`, `.save_labels`, `.save_price`, `.save_raw_articles`, `.save_stat`, `__init__.py`?**
  _High betweenness centrality (0.176) - this node is a cross-community bridge._
- **Why does `RawArticle` connect `Pipeline` to `schema.py`, `ApiRegistry`, `ApiStatus`, `NewsItem`, `.get_connection`, `NewsAPIAdapter`, `.save_raw_articles`, `Database`, `adapters.py`?**
  _High betweenness centrality (0.062) - this node is a cross-community bridge._
- **Why does `ApiError` connect `ApiError` to `DailyQuota`, `ApiRegistry`, `ApiStatus`, `NewsItem`, `test_news_api.py`, `MarketauxAdapter`, `._parse`, `FeedStatus`, `Database`, `EulerpoolAdapter`, `FinnhubAdapter`?**
  _High betweenness centrality (0.032) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Database` (e.g. with `Pipeline` and `PipelineError`) actually correct?**
  _`Database` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Pipeline` (e.g. with `DailyAggregator` and `ArticleCleaner`) actually correct?**
  _`Pipeline` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ApiError` (e.g. with `AlphaVantageAdapter` and `ApiStatus`) actually correct?**
  _`ApiError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `TargetImpact` (e.g. with `DailyAggregator` and `Pipeline`) actually correct?**
  _`TargetImpact` has 6 INFERRED edges - model-reasoned connections that need verification._