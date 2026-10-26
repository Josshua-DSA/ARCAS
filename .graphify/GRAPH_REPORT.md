# Graph Report - .  (2026-10-26)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1985 nodes · 3752 edges · 138 communities (110 shown, 28 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 249 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `7c666ece`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- cli.py
- .compute_ols_hac
- DESIGN — Model, Scoring, Statistik & Antarmuka
- test_manual_ingest.py
- .fetch_prices
- DailyQuota
- BaselineTfidfSentiment
- AlphaVantageAdapter
- news_cli.py
- Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro
- runner.py
- test_dedup.py
- main
- ModelRouter
- test_alloc_profiles_invariant.py
- ApiStatus
- .get_connection
- ApiError
- NewsItem
- test_source_registry.py
- schema.py
- Database
- Dataset Card for Sentiment Analysis of Commodity News (Gold)
- BaseSentimentModel
- test_pipeline_integration.py
- adapters.py
- Pipeline
- PRD — Financial News Sentiment & Market Association System
- RULES — Aturan Wajib Proyek
- Upgrade UI FInews
- test_db.py
- test_news_cli.py
- test_source_health.py
- EulerpoolAdapter
- NewsAPIAdapter
- train
- test_api_no_hardcoded.py
- test_news_crud.py
- PersonaEngine
- Jalur Data — K-3 → A → C → B
- GUI THEME — Claude × Bloomberg
- test_router_config.py
- AUDIT v5 — Database, Backend & ML
- ARCHITECTURE — Financial News Sentiment & Market Association System
- TargetImpact
- FinNews: Financial News Sentiment & Market Association System
- date
- SCHEMA — Data Contracts
- ReportExporter
- AGENTS.md — Panduan untuk AI Agent Kolaborator
- HealthReport
- MarketauxAdapter
- Model Router: Cascade Routing ke Model Spesialis
- Audit Teknis ARCAS — Backend, Model, Data & Infrastruktur
- shell.js
- .seed_aliases
- xau/ — Track FinBERT-EMAS (target XAU)
- .init_schema
- .save_label
- dataset/ — Katalog Data
- splash.js
- Theme & Splash — Bloomberg 70% × Claude 30%
- Model Research Notebooks
- model/ — ML Research & Inference Pipeline (M1–M7)
- research/ — Ringkasan Paper Terkait
- frontend/GUI/ — Static ECharts HTML Dashboard (FR-15)
- graph.sh
- README.md
- __init__.py
- .get_active_universe
- AllocationEngine
- .load
- neutral_band
- TargetRouter
- .get_meta_summary
- FOMCRoBERTaSentiment
- .save_persona_views
- find_skill_dirs
- .save_stat
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
- ArticleSentiment
- test_yfinance_collector.py
- FinbertGoldSentiment
- test_fomc_track.py
- evaluate_holdout.py
- .save_article
- .save_daily_sentiment
- load_fomc_test_holdout
- test_xau_track.py
- load_gold_train
- .route_article
- ._parse_yahoo
- ParquetStore
- TemperatureScaler
- TestPrioritasModel
- evaluate.py
- train_xau_finbert.py
- PriceCollector
- softmax
- train_fomc_roberta.py
- overview.js
- 🏛️ ARCAS — Monetary Policy Track (FOMC)
- TestProbabilityOrder
- research.js
- PriceRecord
- TestSanitize
- train_fomc_baseline
- 1. Aturan Domain
- simulations.js
- 4a. Status Artefak: Apa yang Benar-Benar Bisa Dipakai Hari Ini
- TestTrainedModel
- 14. Fitur Tambahan (v0.3)
- 6. Panduan Menjalankan
- _load_registry
- seeded_db
- temp_db
- 4. Tujuan & Non-Tujuan
- api.js
- .get_impact_for_article
- .query_articles_by_target
- .save_alloc_suggestion
- .save_price
- .sources_needing_alert
- test_parser_has_all_expected_commands

## God Nodes (most connected - your core abstractions)
1. `Database` - 144 edges
2. `Pipeline` - 66 edges
3. `TargetRouter` - 59 edges
4. `Article` - 44 edges
5. `ApiError` - 37 edges
6. `TargetImpact` - 36 edges
7. `NewsItem` - 35 edges
8. `BaselineTfidfSentiment` - 30 edges
9. `EulerpoolAdapter` - 29 edges
10. `RawArticle` - 29 edges

## Surprising Connections (you probably didn't know these)
- `PipelineError` --uses--> `BaselineTfidfSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/common/baseline.py
- `PipelineError` --uses--> `FOMCRoBERTaSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/fomc/src/model.py
- `PipelineStats` --uses--> `BaselineTfidfSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/common/baseline.py
- `PipelineStats` --uses--> `FOMCRoBERTaSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/fomc/src/model.py
- `Pipeline` --uses--> `BaselineTfidfSentiment`  [INFERRED]
  backend/src/pipeline/runner.py → model/common/baseline.py

## Import Cycles
- None detected.

## Communities (138 total, 28 thin omitted)

### Community 0 - "cli.py"
Cohesion: 0.14
Nodes (27): build_parser(), cmd_aggregate(), cmd_clean(), cmd_export(), cmd_ingest(), cmd_pipeline(), cmd_prices(), cmd_report() (+19 more)

### Community 1 - ".compute_ols_hac"
Cohesion: 0.06
Nodes (55): StatResult, Any, DataFrame, date, Deterministic statistical engine for sentiment-market association., Frame bersih: terurut tanggal, kolom `return`, tanpa baris kosong.          Sent, Aturan bandwidth Newey-West: floor(4 * (n/100) ** (2/9))., Regresi OLS `return ~ sentiment` dengan galat standar Newey-West (HAC). (+47 more)

### Community 2 - "DESIGN — Model, Scoring, Statistik & Antarmuka"
Cohesion: 0.04
Nodes (47): 10. Keterbatasan, 11.1 Kelas aset, 11.2 Skor per kelas (`alloc_map.yaml`), 11.3 Rumus, 11.4 Preset profil (contoh, bisa diubah; total wajib 100%), 11.5 Output, 11. Allocation Tilt, 12.1 Persona awal (`personas.yaml`) (+39 more)

### Community 3 - "test_manual_ingest.py"
Cohesion: 0.07
Nodes (50): _baca_csv(), baca_file(), _baca_json(), bangun_artikel(), _baris_ke_artikel(), HasilIngest, _normalisasi_kunci(), _parse_sentimen() (+42 more)

### Community 4 - ".fetch_prices"
Cohesion: 0.24
Nodes (6): date, Ambil harga nyata. Melempar `PriceFetchError` bila gagal.          Tidak ada fal, Seperti `fetch_prices`, tapi mengembalikan asal data secara eksplisit., Fetches real prices for all active core assets.          Satu aset gagal tidak m, Generates synthetic daily price series.          HANYA untuk test/offline simula, Ambil OHLC harian dari Yahoo chart API.          `period1`/`period2` memakai epo

### Community 5 - "DailyQuota"
Cohesion: 0.09
Nodes (32): DailyQuota, Connection, Path, RuntimeError, QuotaExceeded, QuotaStatus, Penjaga kuota request harian — untuk sumber dengan batas 10–100 req/hari.  Menga, Baca pemakaian hari ini tanpa menambah apa pun. (+24 more)

### Community 6 - "BaselineTfidfSentiment"
Cohesion: 0.08
Nodes (24): Tests for baseline ML model and evaluation metrics., Model tanpa fit()/load() harus melempar, bukan mengarang prior.      Sebelum per, fit() pada data kecil harus menghasilkan prediksi valid., Tests F1 macro, accuracy, and kappa computation., test_evaluation_metrics(), test_fit_membuat_model_siap(), test_model_belum_dilatih_melempar(), 01_baseline_exploration.py  Eksplorasi baseline model (M1: TF-IDF + Logistic Reg (+16 more)

### Community 7 - "AlphaVantageAdapter"
Cohesion: 0.21
Nodes (7): AlphaVantageAdapter, Any, ApiSpec, Path, Metadata satu penyedia API., Muat .env bila ada. Tidak melempar bila file tidak ditemukan., _specs()

### Community 8 - "news_cli.py"
Cohesion: 0.11
Nodes (24): datetime, Timestamp UTC timezone-aware — dipakai sebagai fetched_at., Konversi ke kontrak `RawArticle` (SCHEMA)., utcnow(), ApiRegistry, identify_apis(), Nama penyedia yang env var-nya kosong., Laporan kesehatan semua penyedia.          `probe=False` hanya memeriksa keberad (+16 more)

### Community 9 - "Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro"
Cohesion: 0.06
Nodes (31): 1.1 Masalah & Problem Statement, 1.2 Objektif, Metrik Domain, dan Metrik Teknis, 1.3 Uji Kecocokan Solusi (Component Necessity Test), 1. Problem Framing, 2.1 Tujuan Sistem, 2.2 Prinsip Desain, 2.3 Cakupan 3 Target Makro Terkunci (Murni 3 v2026-10-11-p3), 2. Deskripsi Sistem (+23 more)

### Community 10 - "runner.py"
Cohesion: 0.07
Nodes (37): ArticleCleaner, Any, date, datetime, Normalization, deduplication, language detection, and time-alignment., Aligns published datetime to the correct trading date.         Rule: News publis, Prepares raw incoming articles for pipeline consumption., Transforms a RawArticle into a normalized Article contract. (+29 more)

### Community 11 - "test_dedup.py"
Cohesion: 0.07
Nodes (40): _compose(), NearDuplicateDetector, FR-2 / T-6: deteksi artikel near-duplicate.  Dedup yang ada sebelumnya hanya *ex, Kembalikan daftar artikel dengan `duplicate_of` terisi bila perlu.          `his, Teks pembanding: judul diberi bobot lebih dengan cara diulang.      Badan berita, Menandai artikel yang mirip dengan artikel lain via `duplicate_of`., Matriks cosine similarity antar teks. Mengembalikan None bila kosong., _article() (+32 more)

### Community 12 - "main"
Cohesion: 0.12
Nodes (26): main(), Dengan data minim, `stats` harus berhenti dengan pesan jelas (exit 0)., DB kosong: lewati tabel kosong, jangan menulis file palsu., test_export_on_empty_db_does_not_crash(), test_stats_reports_insufficient_pairs_without_crashing(), test_status_runs(), _count(), S-4: test yang menyentuh jalur nyata, bukan hanya komponen terpisah.  AUDIT K-1 (+18 more)

### Community 13 - "ModelRouter"
Cohesion: 0.10
Nodes (24): ModelRouter, Path, Two-stage cascade router: news text -> specialist model id.  Tahap 1: petunjuk s, Lowercase token tanpa stopword. Dipakai builder dan router., Routes an article to the specialist model that should score it., Rata-rata z dan jumlah bukti kuat per domain., Returns (model_ids, reason, score). reason: source|keyword|log_odds|fallback., tokens() (+16 more)

### Community 14 - "test_alloc_profiles_invariant.py"
Cohesion: 0.14
Nodes (23): ProfileConfigError, Path, `alloc_profiles.yaml` melanggar invarian SCHEMA.md #10/#11., Tegakkan invarian SCHEMA.md #10 (Σ base_pct) dan #11 (min/max).          Gagal k, _engine(), Uji invarian konfigurasi profil alokasi (SCHEMA.md #10 & #11).  Latar: `SCHEMA.m, Invarian #11: baseline harus berada di dalam [min_pct, max_pct]., Pesan harus menyebut profil mana — YAML bisa berisi banyak profil. (+15 more)

### Community 15 - "ApiStatus"
Cohesion: 0.12
Nodes (22): Adapter Alpha Vantage NEWS_SENTIMENT.  Endpoint: GET /query?function=NEWS_SENTIM, ApiStatus, Enum, str, Primitif bersama untuk seluruh adapter news API., Hasil identifikasi satu penyedia API., env(), NewsAPIClient (+14 more)

### Community 16 - ".get_connection"
Cohesion: 0.07
Nodes (10): Queries recent econometric results for asset., Baca kembali persona_views yang tersimpan (untuk audit)., Baca kembali alloc_suggestions yang tersimpan (untuk audit)., Status terakhir tiap sumber, satu baris per sumber.          Memakai `rowid` seb, Stores a raw (unnormalized) article. Returns raw_id.          Deduplikasi memaka, Returns raw articles, terbaru dulu., Bulk insert normalized articles. Returns jumlah baris ditulis., Stores all ModelProbs for an article (satu baris per model). (+2 more)

### Community 17 - "ApiError"
Cohesion: 0.10
Nodes (19): ApiError, Any, GET JSON dengan retry. Melempar `ApiError` setelah percobaan habis.          `he, GET teks mentah (untuk RSS/XML)., Kegagalan HTTP yang sudah diklasifikasi., _clean(), _parse_date(), datetime (+11 more)

### Community 18 - "NewsItem"
Cohesion: 0.09
Nodes (26): NewsItem, Satu berita mentah, belum dinormalisasi (belum punya article_id)., FinnhubAdapter, Any, Tarik berita relevan untuk satu target.          Menggabungkan beberapa kategori, count_hits(), _pattern(), Jumlah kata kunci berbeda yang cocok di teks. (+18 more)

### Community 19 - "test_source_registry.py"
Cohesion: 0.08
Nodes (22): _load_feeds(), Path, Baca `targets.<ID>.feeds` dari registry.      Hanya entri ber-`type: rss` yang d, T-4 / FR-3: registry YAML adalah satu-satunya sumber kebenaran.  Sebelum perbaik, Entri non-RSS (mis. deklarasi API) tidak boleh masuk daftar feed., Registry hilang: program tetap hidup, tetapi jujur soal sumbernya., Cadangan harus jauh lebih kecil dari registry asli.      Kalau cadangan sama pan, Regresi: pindah ke YAML tidak boleh mengurangi cakupan routing.      Daftar lama (+14 more)

### Community 20 - "schema.py"
Cohesion: 0.09
Nodes (37): Deterministic Persona POV engine computing BUY/HOLD/SELL stances., AssetClass, Basis, Direction, EvidenceSpan, NewsHorizon, Enum, str (+29 more)

### Community 21 - "Database"
Cohesion: 0.11
Nodes (15): _latest_scores(), Ambil skor sentimen terakhir per aset dari DB.      Mengembalikan (scores, sourc, Database, Manages SQLite connections and queries for FInews., Stores a TargetImpact record., Bulk insert. Returns jumlah baris baru., Bulk insert labels. Each dict: article_id, asset_id, annotator, label., Database and storage repository. (+7 more)

### Community 22 - "Dataset Card for Sentiment Analysis of Commodity News (Gold)"
Cohesion: 0.09
Nodes (22): Acknowledgements, Bias, Risks, and Limitations, Citation, Content, Context, Curation Rationale, Data Collection and Processing, Data Fields (+14 more)

### Community 23 - "BaseSentimentModel"
Cohesion: 0.16
Nodes (8): ABC, BaseSentimentModel, Abstract base protocol for sentiment inference models., Protocol for financial sentiment classifiers., Name of the model architecture., Returns 3-class probabilities [p_pos, p_neu, p_neg] summing to 1.0., Returns structured ArticleSentiment., FinBERT-EMAS: inference wrapper untuk track XAU (M2) + trainer (M6).  Mengimplem

### Community 24 - "test_pipeline_integration.py"
Cohesion: 0.18
Nodes (17): _count(), db_path(), _iso(), datetime, Path, Test integrasi end-to-end: raw_articles -> articles -> impacts -> daily_sentimen, Menjalankan dua kali tidak boleh menggandakan baris., --dry-run menghitung tapi tidak menyentuh database. (+9 more)

### Community 25 - "adapters.py"
Cohesion: 0.20
Nodes (18): fomc_stance(), fomc_to_raw(), fomc_tone(), _gold_parse_date(), gold_to_raw(), gold_tone(), DataFrame, datetime (+10 more)

### Community 26 - "Pipeline"
Cohesion: 0.07
Nodes (36): Pipeline, PipelineStats, Menyambungkan komponen-komponen menjadi satu alur berjalan., Mengisi asset_master & asset_aliases.          Tanpa ini `/api/universe` mengemb, Memuat model sentimen. Gagal keras bila tidak ada.          AUDIT K-4: lebih bai, raw_articles -> Article, lalu tulis ke tabel `articles`., Baca kembali `Article` dari tabel `articles`.          S-4: `cmd_score` dulu mem, Tandai near-duplicate terhadap riwayat DB dan sesama batch.          Artikel dup (+28 more)

### Community 27 - "PRD — Financial News Sentiment & Market Association System"
Cohesion: 0.15
Nodes (13): 10. Sumber Data (ringkas; detail di `ARCHITECTURE.md` §4), 11. Fase, 12. Risiko, 13. Open Questions, 1. Ringkasan, 2. Universe Terkunci (v2026-10-11, fokus supervised v2026-10-11) + Satu Track Model, 3. Masalah, 5. Pengguna & User Stories (+5 more)

### Community 28 - "RULES — Aturan Wajib Proyek"
Cohesion: 0.14
Nodes (14): 10. Untuk AI Assistant yang Mengerjakan Repo Ini, 11.1 Aturan Frontend (GUI Web & TUI), 11. Aturan Allocation Tilt & Persona POV (v0.3), 2. Aturan Data, 3. Aturan Pelabelan, 4. Aturan Model & Evaluasi, 5. Aturan Analisis Statistik, 6. Dihapus (tanpa LLM/RAG/Agent) (+6 more)

### Community 29 - "Upgrade UI FInews"
Cohesion: 0.10
Nodes (20): 1. Tujuan, 2. Kondisi UI Saat Ini, 3.1 Adaptasi Splash Screen yang Sudah Ada, 3. Struktur Halaman yang Direkomendasikan, 4. Prioritas Upgrade, 5. Perubahan Kontrak Minimum, 6. Urutan Implementasi, 7. Yang Sengaja Tidak Dibuat (+12 more)

### Community 30 - "test_db.py"
Cohesion: 0.12
Nodes (16): Tests for SQLite database initialization, seeding, and operations., `init_schema()` aman dipanggil berulang — sifat yang tadinya     tersembunyi di, Alias yang membingungkan tidak boleh kembali., Verifies that asset_master and aliases are properly seeded., get_meta_summary returns real counts and version stamps for /api/meta., Time audit join degrades to real empties, never fake timestamps., Tests saving and querying daily sentiments., Tests price storage and retrieval. (+8 more)

### Community 31 - "test_news_cli.py"
Cohesion: 0.09
Nodes (37): build_parser(), _dedupe(), main(), _print_alerts(), ArgumentParser, Buang duplikat lintas penyedia berdasarkan judul ternormalisasi., Simpan hasil pemeriksaan ke `source_health` dan kembalikan daftar alert.      Di, _record_health() (+29 more)

### Community 32 - "test_source_health.py"
Cohesion: 0.10
Nodes (12): db(), Tests for T-3: riwayat kesehatan sumber & alert (FR-18).  Yang diuji bukan sekad, Detail sangat panjang tidak boleh menggembungkan tabel tanpa batas., Satu-dua kegagalan belum boleh memicu alert., Setelah sumber pulih, alert harus berhenti -- bukan menyala selamanya., `no_key` adalah pilihan konfigurasi, bukan sumber yang mati., Pemeriksaan dalam detik yang sama tidak boleh menghasilkan baris ganda.      `ch, test_alert_clears_after_recovery() (+4 more)

### Community 33 - "EulerpoolAdapter"
Cohesion: 0.19
Nodes (11): EulerpoolAdapter, Any, datetime, Satu panggilan HTTP. Memesan kuota lebih dulu bila dijaga.          `limit` di-c, `datetime` dari Eulerpool berupa epoch detik (int)., Tolak berita lebih tua dari MAX_AGE_DAYS atau bertanggal masa depan., Cek kunci dengan satu request minimum (limit=1)., Tarik berita relevan untuk satu target.          Biaya kuota: **1 request**, ber (+3 more)

### Community 34 - "NewsAPIAdapter"
Cohesion: 0.20
Nodes (6): NewsAPIAdapter, Protocol, Tarik berita untuk satu target universe., Kontrak setiap adapter penyedia berita., True bila kredensial tersedia., Uji ringan: kunci valid? ada data?

### Community 35 - "train"
Cohesion: 0.33
Nodes (8): load_split(), main(), _proba_matrix(), Path, Melatih baseline TF-IDF + LR dari dataset gold_sinha (nyata, berlabel).  Dataset, Membaca satu split parquet, mengembalikan (texts, labels)., Melatih dan menyimpan model. Mengembalikan metrik evaluasi., train()

### Community 36 - "test_api_no_hardcoded.py"
Cohesion: 0.10
Nodes (23): create_app(), Path, FastAPI REST application for FinNews., Creates and configures the FastAPI application., FastAPI REST application., client(), Tests for S-1: endpoint API tidak boleh menyajikan angka karangan.  Sebelum perb, Parameter eksplisit tetap boleh menimpa DB (untuk eksplorasi). (+15 more)

### Community 37 - "test_news_crud.py"
Cohesion: 0.18
Nodes (16): _article(), db(), Test untuk CRUD tabel berita (K-3) dan kolektor RSS., _raw(), test_get_missing_article_returns_none(), test_query_articles_by_target_joins_articles(), test_query_raw_articles_filters_by_source(), test_save_and_get_article() (+8 more)

### Community 38 - "PersonaEngine"
Cohesion: 0.17
Nodes (10): PersonaEngine, Path, Evaluates 5 investor personas stances for a given impact., Calculates decay/alignment between news horizon and persona horizon., Calculates stance for a specific persona based on parameters.         Determinis, Evaluates all 5 personas., Persona POV simulation engine., PersonaView (+2 more)

### Community 39 - "Jalur Data — K-3 → A → C → B"
Cohesion: 0.12
Nodes (15): Batasan yang perlu diketahui, Feed terverifikasi hidup, Feed yang dibuang (jangan dipakai lagi), Identifikasi API, Jalur A — Harga, Jalur B — Berita via RSS, Jalur C — Berita via API, Jalur Data — K-3 → A → C → B (+7 more)

### Community 40 - "GUI THEME — Claude × Bloomberg"
Cohesion: 0.12
Nodes (15): 10. Tipografi (ringkas; versi font gratis padanan), 11. CSS Variables (siap salin), 12. Konfigurasi Streamlit (jika dipakai; cek dukungan font kustom pada versi yang dipakai), 13. Daftar Periksa Implementasi, 1. Konsep, 2. Warna Inti (dari spesifikasi), 3. Token Turunan — Sisi Terang, 4. Token Turunan — Sisi Gelap (Technical Surface) (+7 more)

### Community 41 - "test_router_config.py"
Cohesion: 0.17
Nodes (14): Tests for T-5: ambang & kalibrasi router berasal dari YAML, bukan kode.  Alasan, Router yang membaca config dari tmp_path (bukan data/ asli)., Nilai bawaan harus identik dengan angka yang dulu ditanam di kode.      Kalau be, Plafon keyakinan makro tidak boleh terlampaui berapa pun bobotnya., Menaikkan ambang harus bisa memaksa arah menjadi NETRAL., YAML rusak tidak boleh membuat router mati total., _router(), test_broken_yaml_falls_back_to_defaults() (+6 more)

### Community 42 - "AUDIT v5 — Database, Backend & ML"
Cohesion: 0.14
Nodes (13): 1. FR-6 / K-3 · FinBERT XAU belum ada — **P0, satu-satunya yang kosong**, 2. FR-3 · entitas non-emas belum masuk `asset_aliases` — **P0, parsial**, 3. FR-1 sisa · scraper ID (detik/kompas/antara) — **P0, ditunda**, AUDIT v5 — Database, Backend & ML, Cakupan Test, Catatan Metodologi, Kenapa v5 ini ada, Ringkasan Angka (kondisi `2742e48`) (+5 more)

### Community 43 - "ARCHITECTURE — Financial News Sentiment & Market Association System"
Cohesion: 0.14
Nodes (13): 10. Kontrak Penyajian, 11. Modul Tambahan v0.3, 1. Gambaran Umum, 2. Lapisan, 3. Tahap Pipeline, 4. Sumber Data & Source Registry, 5. Orkestrasi, 6. Struktur Repo (+5 more)

### Community 44 - "TargetImpact"
Cohesion: 0.08
Nodes (28): DailyAggregator, date, Aggregates article impacts into daily sentiment series., Computes daily mean and weighted sentiment per target., Aggregates impacts for a single asset on a given trading date.         Strict in, Aggregates batch of impacts, explicitly creating empty records         with scor, Daily sentiment aggregation across assets., impacts -> daily_sentiment. (+20 more)

### Community 45 - "FinNews: Financial News Sentiment & Market Association System"
Cohesion: 0.15
Nodes (12): 1. Prasyarat & Instalasi, 2. Menjalankan Unit Test, 3. Eksplorasi Baseline Model (ML Offline), 4. Menjalankan Server API Backend, 🏛️ Arsitektur Sistem (3-Tier Layer), 🔒 Aturan Desain & Integritas Kuantitatif, FinNews: Financial News Sentiment & Market Association System, 🎯 Murni 3 Supervised (`XAU` / `RATE_UST` / `SPX`) (+4 more)

### Community 47 - "date"
Cohesion: 0.17
Nodes (6): date, Retrieves joint sentiment and price series for a target., Stores one article→target mapping., Bulk insert mappings untuk satu artikel. Returns jumlah baris., Queries daily sentiment records between dates., Queries price records between dates.

### Community 48 - "SCHEMA — Data Contracts"
Cohesion: 0.17
Nodes (11): 1. Enum, 2. Model Pipeline (Pydantic v2), 3. Output JSON (contoh), 4. Universe (`asset_master`), 5. Source Registry & Impact Graph, 6. Tabel Database (SQL), 7. Invarian (wajib dijaga validator), 8.1 Kontrak Role (+3 more)

### Community 49 - "ReportExporter"
Cohesion: 0.10
Nodes (17): Any, Path, Generates static HTML and JSON analytical reports into outputs/., Exports system analytical snapshots and statistics., Exports analytical JSON snapshot., Renders self-contained static HTML report for the 3 core targets., ReportExporter, Report export utilities. (+9 more)

### Community 50 - "AGENTS.md — Panduan untuk AI Agent Kolaborator"
Cohesion: 0.20
Nodes (9): 1. Mulai dari sini, bukan dari `ls -R`, 2. Peta cepat: di mana apa, 3. Aturan yang tidak boleh dilanggar, 4. Lingkup kerja per peran, 5. Perintah yang sering dipakai, 6. Konvensi commit, 7. Kondisi repository saat ini, 8. Saat ragu (+1 more)

### Community 51 - "HealthReport"
Cohesion: 0.20
Nodes (7): HealthReport, Any, Ringkasan kesehatan satu penyedia API., FeedStatus, Uji satu feed tanpa melempar., Kesehatan semua feed (atau hanya milik satu target)., Versi `HealthReport` agar seragam dengan adapter API.

### Community 52 - "MarketauxAdapter"
Cohesion: 0.46
Nodes (3): MarketauxAdapter, Any, test_marketaux_without_key_is_not_configured()

### Community 53 - "Model Router: Cascade Routing ke Model Spesialis"
Cohesion: 0.20
Nodes (9): Arsitektur: dua tahap + fallback, Batasan yang diketahui, Cara menjalankan, Jejak audit, Masalah, Mengapa aturan bukti, bukan rata-rata, Model Router: Cascade Routing ke Model Spesialis, Tahap 1 — sumber dan kata kunci (+1 more)

### Community 54 - "Audit Teknis ARCAS — Backend, Model, Data & Infrastruktur"
Cohesion: 0.08
Nodes (25): 0. Ringkasan, 1. Temuan Kritis (P0), 2. Temuan Penting (P1), 3. Temuan Sedang (P2), 4. Temuan Ringan (P3), 5. Yang Sudah Baik (jangan diubah), 6. Prioritas Perbaikan, 7. Cara Mereproduksi Audit Ini (+17 more)

### Community 55 - "shell.js"
Cohesion: 0.12
Nodes (18): applyNewsFilter(), bindPersonaButtons(), evidenceDrawer(), impactCard(), renderAll(), renderImpacts(), timeAuditLine(), bindTabs() (+10 more)

### Community 56 - ".seed_aliases"
Cohesion: 0.33
Nodes (3): Path, Seeds the 3 core locked assets from asset_master.csv., Seeds asset aliases from aliases.csv.

### Community 58 - "xau/ — Track FinBERT-EMAS (target XAU)"
Cohesion: 0.18
Nodes (10): Artefak: tidak di-commit, Cara pakai, Catatan lingkungan (penting sebelum menjalankan training), Catatan teknis yang mudah salah, Kerangka, Keterbatasan, Kontrak, Sumber data (jujur, bukan sesuai nama folder) (+2 more)

### Community 59 - ".init_schema"
Cohesion: 0.40
Nodes (3): Connection, Initializes tables and indexes, lalu migrasi kolom yang menyusul., Menambah kolom baru pada DB lama. Idempoten dan aman diulang.

### Community 60 - ".save_label"
Cohesion: 0.40
Nodes (3): datetime, Catat satu hasil pemeriksaan kesehatan sumber.          Mengembalikan jumlah keg, Stores one human annotation.

### Community 61 - "dataset/ — Katalog Data"
Cohesion: 0.40
Nodes (4): dataset/ — Katalog Data, Dihapus 2026-10-11, Mapping label (beku), Sitasi

### Community 62 - "splash.js"
Cohesion: 0.38
Nodes (4): markAllDone(), stamp(), status(), tryFinish()

### Community 63 - "Theme & Splash — Bloomberg 70% × Claude 30%"
Cohesion: 0.40
Nodes (4): Catatan, Streamlit, Theme & Splash — Bloomberg 70% × Claude 30%, Web biasa

### Community 65 - "Model Research Notebooks"
Cohesion: 0.50
Nodes (3): Model Research Notebooks, Standar Output Artefak:, Struktur Notebook:

### Community 66 - "model/ — ML Research & Inference Pipeline (M1–M7)"
Cohesion: 0.50
Nodes (3): Aturan pembagian, model/ — ML Research & Inference Pipeline (M1–M7), Pemetaan Modul (M1–M7)

### Community 67 - "research/ — Ringkasan Paper Terkait"
Cohesion: 0.50
Nodes (3): 1. Paper Utama & Pendukung (Tersimpan di `research/papers/`), 2. Sintesis untuk Sidang Skripsi / TA, research/ — Ringkasan Paper Terkait

### Community 73 - "AllocationEngine"
Cohesion: 0.14
Nodes (20): AllocationEngine, Deterministic Allocation Tilt engine satisfying strict 100% sum constraint., Derives scores for 6 allocation classes using alloc_map.yaml.         Score tupl, Calculates constrained allocation tilt for a specific profile.         Strictly, Computes relative portfolio tilt adjustments from asset scores., Allocation Tilt simulation engine., AllocationLine, AllocationSuggestion (+12 more)

### Community 74 - ".load"
Cohesion: 0.22
Nodes (7): Model nyata harus memberi sinyal berbeda untuk teks bullish vs bearish., test_model_terlatih_membedakan_arah(), Model terlatih harus memberi skor berbeda untuk teks berbeda.      Test ini meng, test_model_memuat_dan_memberi_sinyal_berbeda(), Path, Memuat model terlatih dari disk., Menyimpan model terlatih ke disk (joblib).

### Community 75 - "neutral_band"
Cohesion: 0.11
Nodes (21): XAU harus ada di peta arah; sebelumnya hanya RATE_UST/SPX., Path, RULES.md: ambang wajib di config, dan berkasnya harus konsisten., Berkas hilang tidak boleh mematikan model; dipakai nilai bawaan., `neutral_band` di luar [0, 1] diabaikan agar skor tidak selalu netral., Database SQLite sementara dengan skema lengkap., temp_db(), test_ambang_netral_dari_config_bukan_literal() (+13 more)

### Community 76 - "TargetRouter"
Cohesion: 0.06
Nodes (34): Target tagging and impact graph traversal., Path, Tags targets and projects macro impact from text., TargetRouter, Mengubah kebijakan di YAML harus mengubah hasil, bukan hanya dokumen., router(), test_policy_comes_from_yaml(), _article() (+26 more)

### Community 78 - "FOMCRoBERTaSentiment"
Cohesion: 0.12
Nodes (11): Any, Path, Memuat model spesialis FinBERT-EMAS secara lazy (FR-6).          Mengembalikan `, Memuat model spesialis FOMC-RoBERTa secara lazy., FOMCRoBERTaSentiment, ndarray, Loads Hugging Face tokenizer and model onto target device., Runs batched inference and returns unnormalized logits tensor of shape (N, 3). (+3 more)

### Community 80 - "find_skill_dirs"
Cohesion: 0.38
Nodes (6): find_skill_dirs(), main(), patch_text(), Path, Semua direktori skill graphify yang terpasang., Terapkan semua perbaikan. Kembalikan (teks_baru, berubah).      Idempoten: blok

### Community 94 - "ArticleSentiment"
Cohesion: 0.13
Nodes (23): ArticleSentiment, ModelProbs, Tone, AUDIT v3 §2: duplikat tidak ikut diskor / menambah hitungan.      Memakai model, test_duplicate_does_not_increase_daily_article_count(), _create_sample_article(), Test integrasi Pipeline Runner dengan Model Spesialis FOMC-RoBERTa (Track B).  M, Artikel FOMC dovish memicu tema rates_down dan menghasilkan dampak SPX, RATE_UST (+15 more)

### Community 95 - "test_yfinance_collector.py"
Cohesion: 0.15
Nodes (11): PriceFetchError, RuntimeError, Gagal mengambil harga nyata dari penyedia.      Dilempar alih-alih mengembalikan, Uji `PriceCollector` (backend/src/collect/yfinance_collector.py).  Modul ini seb, Kegagalan jaringan tidak boleh diam-diam jadi data sintetis., Satu aset gagal tidak menghentikan yang lain; error dicatat., test_fetch_failure_raises_instead_of_returning_synthetic(), test_fetch_universe_continues_when_one_asset_fails() (+3 more)

### Community 96 - "FinbertGoldSentiment"
Cohesion: 0.15
Nodes (8): FinbertGoldSentiment, ndarray, Path, Versi dari metrics.json bila ada, agar dapat diaudit per-artefak., Kembalikan probabilitas terkalibrasi, urutan `[pos, neu, neg]`., Logits mentah (untuk temperature scaling saat kalibrasi).          Urutan kolom, Skor satu artikel → ArticleSentiment terkalibrasi.          Ambang ±0.10 sama de, FinBERT yang di-fine-tune pada korpus berita emas Sinha.

### Community 97 - "test_fomc_track.py"
Cohesion: 0.13
Nodes (15): Unit tests for FOMC track data loader and methodology contracts., Validates BaseSentimentModel protocol compliance without downloading heavy check, Validates bootstrap 95% confidence interval for difference in Macro F1., Validates that train set loads exactly 1.939 valid rows with required columns., Validates stratified 90:10 split (1.745 train vs 194 validation)., Validates that official unseen test set has exactly 495 rows., Validates monetary stance transmission invariant to RATE_UST and SPX., test_compute_bootstrap_ci() (+7 more)

### Community 98 - "evaluate_holdout.py"
Cohesion: 0.16
Nodes (14): Validates multi-class Expected Calibration Error (ECE) metric., Validates McNemar 2x2 contingency table calculation and p-value., test_compute_mcnemar_significance(), test_multiclass_ece_calculation(), compute_mcnemar_test(), evaluate_holdout(), main(), Path (+6 more)

### Community 101 - "load_fomc_test_holdout"
Cohesion: 0.21
Nodes (15): Validates extracting clean lists of texts and integer labels., test_get_fomc_texts_and_labels(), get_fomc_texts_and_labels(), load_fomc_test_holdout(), load_fomc_train_raw(), load_fomc_train_val_split(), DataFrame, Path (+7 more)

### Community 102 - "test_xau_track.py"
Cohesion: 0.15
Nodes (10): Test track FinBERT-EMAS (FR-6 / M2 + M6).  Fokus pada hal yang **tidak butuh PyT, Mapping label harus cocok dengan protokol dan adapters backend., README model/xau menetapkan Positive→2, Neutral→1, Negative→0., Loader model dan jalur ingest harus memetakan tone dengan cara sama.          Ka, Baris `none` harus hilang, bukan berubah jadi neutral., TestLabelContract, normalize_tone(), Petakan nilai `Price Sentiment` mentah ke tone baku, atau None.      None berart (+2 more)

### Community 103 - "load_gold_train"
Cohesion: 0.24
Nodes (12): Duplikat antar-split akan membocorkan contoh test ke train., load_gold_test(), load_gold_test_holdout(), load_gold_train(), load_gold_train_raw(), DataFrame, Path, Loader korpus `dataset/gold_sinha/` → teks + label tone 3 kelas.  Kontrak label (+4 more)

### Community 104 - ".route_article"
Cohesion: 0.18
Nodes (8): _alias_pattern(), Arah aset terhadap stance hawkish (+1/-1).          Aset yang tidak terdaftar di, Skor dalam ruang arah harga untuk satu aset.          Mode `price`: skor sudah b, Finds direct alias matches in text.         Returns list of (asset_id, matched_a, Kompilasi alias menjadi regex word-boundary, case-insensitive.      Spasi/tanda, Deteksi tema makro dari kata kunci ID + EN (word-boundary)., Routes an article to target impacts via explicit mentions and macro themes., Pattern

### Community 105 - "._parse_yahoo"
Cohesion: 0.24
Nodes (11): Hari libur / bar tidak lengkap harus dilewati, bukan jadi 0., Bila open/high/low None, pakai close -- jangan hasilkan None., Timestamp ada tapi semua close null -> tidak boleh mengembalikan []., Payload hasil json.loads (bukan dict langsung) juga harus terbaca., test_parse_yahoo_falls_back_to_close_for_missing_ohlc(), test_parse_yahoo_json_roundtrip(), test_parse_yahoo_produces_records_with_utc_dates(), test_parse_yahoo_raises_when_no_valid_bar() (+3 more)

### Community 106 - "ParquetStore"
Cohesion: 0.20
Nodes (8): ParquetStore, Any, DataFrame, Path, Parquet storage helpers for bulk dumps and training datasets., Manages Parquet writes and reads for processed time series., Saves records to a Parquet file., Reads records from a Parquet file.

### Community 107 - "TemperatureScaler"
Cohesion: 0.21
Nodes (8): Validates TemperatureScaler fitting, scaling, and JSON persistence., test_temperature_scaler_fit_and_persistence(), Path, Saves temperature calibration metadata to JSON file., Loads temperature parameter from JSON file., Scales logits by optimal temperature parameter T to calibrate prediction probabi, TemperatureScaler, Path

### Community 108 - "TestPrioritasModel"
Cohesion: 0.17
Nodes (6): P0-3: prioritas model adalah data eksplisit, bukan urutan `if`., Tiap baris harus punya loader & `score_space` yang sah., FOMC mengukur stance; kalau ditandai `price`, P0-2 kembali bug., FinBERT-EMAS dilatih pada sentimen harga emas, bukan stance Fed., Nama loader harus benar-benar ada, bukan string mati., TestPrioritasModel

### Community 109 - "evaluate.py"
Cohesion: 0.26
Nodes (9): evaluate(), main(), _print_summary(), Any, Path, Evaluasi artefak FinBERT-EMAS pada holdout test (M6).  Jalankan setelah training, get_texts_and_labels(), Ambil pasangan (teks, label) siap umpan ke tokenizer. (+1 more)

### Community 110 - "train_xau_finbert.py"
Cohesion: 0.26
Nodes (11): Pisahkan validation dari train untuk early stopping + temperature.      Stratifi, split_train_val(), _class_report(), _macro_f1(), main(), Any, ndarray, Path (+3 more)

### Community 111 - "PriceCollector"
Cohesion: 0.20
Nodes (8): Market data and news collectors., PriceCollector, Path, Fetches daily prices for core locked universe assets., collector(), Kolektor dengan peta ticker buatan sendiri (tidak menyentuh data repo)., Tanpa file master, kolektor tetap dibuat; fetch yang akan menolak., test_missing_asset_master_is_not_fatal()

### Community 112 - "softmax"
Cohesion: 0.22
Nodes (8): Validates invariant that probabilities always sum to 1.0 and soften with higher, test_softmax_temperature_properties(), ndarray, Finds optimal temperature T by minimizing Negative Log-Likelihood (NLL) on valid, Scales raw logits by learned temperature: z / T., Converts raw logits to calibrated probabilities summing to 1.0., Computes numerically stable softmax probabilities with temperature scaling., softmax()

### Community 113 - "train_fomc_roberta.py"
Cohesion: 0.29
Nodes (10): _class_report(), _macro_f1(), main(), Any, ndarray, Path, Latih FOMC-RoBERTa pada korpus FOMC (P0-1).  Resep mengikuti rilis upstream yang, Presisi/recall/F1 per kelas — tanpa ini, rata-rata menyembunyikan neutral. (+2 more)

### Community 114 - "overview.js"
Cohesion: 0.38
Nodes (9): bindPager(), ensureChart(), isoDaysAgo(), newsItem(), renderAll(), renderChart(), renderNews(), renderNewsPage() (+1 more)

### Community 115 - "🏛️ ARCAS — Monetary Policy Track (FOMC)"
Cohesion: 0.22
Nodes (9): 1. Hasil Benchmark Resmi (Holdout 495 Sampel Beku), 2. Preprocessing Khusus Domain Finansial FOMC, 3. Arsitektur Pipeline End-to-End ARCAS, 4. Mekanisme Fail-Safe: Dual-Checkpoint Auto-Fallback, 5. Struktur Direktori Track FOMC, 7. Sitasi Akademik, 🏛️ ARCAS — Monetary Policy Track (FOMC), Dual-Target Financial Sentiment & Market Association Engine (+1 more)

### Community 116 - "TestProbabilityOrder"
Cohesion: 0.25
Nodes (5): Path, Urutan probabilitas harus [pos, neu, neg] sesuai protokol., Simulasi: logits condong ke kelas 2 (positive) harus jadi p_pos tertinggi., Tanpa artefak, error harus menuntun ke skrip latih, bukan segfault., TestProbabilityOrder

### Community 117 - "research.js"
Cohesion: 0.43
Nodes (7): metricLabel(), pct(), renderAll(), renderQuality(), renderWorkbench(), runWorkbench(), updateWorkbenchControls()

### Community 118 - "PriceRecord"
Cohesion: 0.38
Nodes (5): FetchResult, Price data collector for the 3 core locked assets (XAU, RATE_UST, SPX).  Sumber, Hasil satu penarikan harga, termasuk asal datanya., PriceRecord, test_fetch_with_meta_marks_source_as_yahoo()

### Community 119 - "TestSanitize"
Cohesion: 0.29
Nodes (3): Neutral hanya ~4%; stratifikasi menjamin ia hadir di validation., Kebersihan data nyata pada parquet lokal., TestSanitize

### Community 120 - "train_fomc_baseline"
Cohesion: 0.33
Nodes (6): Validates training and serializing the FOMC baseline TF-IDF + LR model., test_train_fomc_baseline(), LogisticRegression, DataFrame, Trains Baseline TF-IDF + Logistic Regression on FOMC train set.      Label mappi, train_fomc_baseline()

### Community 121 - "1. Aturan Domain"
Cohesion: 0.33
Nodes (6): 1.1 Definisi, 1.2 `basis` dan batas confidence, 1.3 Evidence & rationale, 1.4 Target, 1.5 Disclaimer, 1. Aturan Domain

### Community 122 - "simulations.js"
Cohesion: 0.60
Nodes (5): chipArah(), fmtSkor(), renderAll(), renderPersonaCards(), renderVersions()

### Community 123 - "4a. Status Artefak: Apa yang Benar-Benar Bisa Dipakai Hari Ini"
Cohesion: 0.40
Nodes (5): 4a. Status Artefak: Apa yang Benar-Benar Bisa Dipakai Hari Ini, Batas kemampuan baseline FOMC, Cara mengaktifkan RoBERTa, Ingin setara XAU?, Konsekuensi praktis

### Community 125 - "14. Fitur Tambahan (v0.3)"
Cohesion: 0.50
Nodes (4): 14.1 Allocation Tilt, 14.2 Persona POV (5 persona), 14.3 Catatan Penting, 14. Fitur Tambahan (v0.3)

### Community 126 - "6. Panduan Menjalankan"
Cohesion: 0.50
Nodes (4): 6. Panduan Menjalankan, A. Evaluasi Holdout Mandiri via CLI, B. Menjalankan Unit Testing Otomatis, C. Eksplorasi Interaktif via Notebook (Opsi B)

### Community 127 - "_load_registry"
Cohesion: 0.67
Nodes (3): _load_registry(), Path, Baca `targets.<ID>.keywords` dan `macro.keywords` dari registry.      Returns:

### Community 128 - "seeded_db"
Cohesion: 0.67
Nodes (3): Path, Database dengan skema lengkap dan raw_articles siap olah., seeded_db()

### Community 129 - "temp_db"
Cohesion: 0.67
Nodes (3): Path, Database SQLite sementara dengan skema lengkap., temp_db()

### Community 130 - "4. Tujuan & Non-Tujuan"
Cohesion: 0.67
Nodes (3): 4. Tujuan & Non-Tujuan, Goals, Non-Goals (v1)

## Knowledge Gaps
- **272 isolated node(s):** `finews`, `graph.sh script`, `GRAPHIFY_OUT`, `1. Mulai dari sini, bukan dari `ls -R``, `2. Peta cepat: di mana apa` (+267 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **28 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `cli.py`, `.compute_ols_hac`, `seeded_db`, `temp_db`, `test_manual_ingest.py`, `.get_impact_for_article`, `.query_articles_by_target`, `.save_alloc_suggestion`, `news_cli.py`, `.save_price`, `runner.py`, `.sources_needing_alert`, `main`, `test_dedup.py`, `.get_connection`, `schema.py`, `test_pipeline_integration.py`, `Pipeline`, `test_db.py`, `test_news_cli.py`, `test_source_health.py`, `test_api_no_hardcoded.py`, `test_news_crud.py`, `TargetImpact`, `date`, `.seed_aliases`, `.init_schema`, `.save_label`, `.get_active_universe`, `neutral_band`, `TargetRouter`, `.get_meta_summary`, `.save_persona_views`, `.save_stat`, `ArticleSentiment`, `.save_article`, `.save_daily_sentiment`, `PriceRecord`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Why does `RawArticle` connect `runner.py` to `NewsAPIAdapter`, `test_manual_ingest.py`, `test_news_crud.py`, `news_cli.py`, `AllocationEngine`, `ApiStatus`, `.get_connection`, `NewsItem`, `HealthReport`, `schema.py`, `Database`, `adapters.py`, `Pipeline`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Why does `Pipeline` connect `Pipeline` to `cli.py`, `BaselineTfidfSentiment`, `runner.py`, `test_dedup.py`, `TargetImpact`, `TargetRouter`, `FOMCRoBERTaSentiment`, `ModelRouter`, `TestPrioritasModel`, `Database`, `test_pipeline_integration.py`, `ArticleSentiment`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Database` (e.g. with `Pipeline` and `PipelineError`) actually correct?**
  _`Database` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Pipeline` (e.g. with `DailyAggregator` and `ArticleCleaner`) actually correct?**
  _`Pipeline` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `TargetRouter` (e.g. with `Pipeline` and `PipelineError`) actually correct?**
  _`TargetRouter` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Article` (e.g. with `ArticleCleaner` and `NearDuplicateDetector`) actually correct?**
  _`Article` has 10 INFERRED edges - model-reasoned connections that need verification._