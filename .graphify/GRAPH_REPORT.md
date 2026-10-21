# Graph Report - FInews  (2026-10-21)

## Corpus Check
- 111 files · ~108,522 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1468 nodes · 2770 edges · 98 communities (72 shown, 26 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 191 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f733998d`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- cli.py
- .compute_ols_hac
- DESIGN — Model, Scoring, Statistik & Antarmuka
- app.js
- PriceRecord
- DailyQuota
- ModelNotFittedError
- HealthReport
- news_cli.py
- Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro
- Article
- test_dedup.py
- main
- ModelRouter
- AllocationEngine
- ApiStatus
- .get_connection
- ApiError
- test_news_api.py
- test_source_registry.py
- test_news_horizon.py
- test_router_db_integration.py
- Dataset Card for Sentiment Analysis of Commodity News (Gold)
- ArticleSentiment
- Pipeline
- adapters.py
- PipelineStats
- PRD — Financial News Sentiment & Market Association System
- RULES — Aturan Wajib Proyek
- Upgrade UI FInews
- TargetImpact
- schema.py
- test_source_health.py
- EulerpoolAdapter
- _latest_scores
- ReportExporter
- db.py
- Database
- NewsHorizon
- Jalur Data — K-3 → A → C → B
- GUI THEME — Claude × Bloomberg
- TargetRouter
- AUDIT v4 — Database, Backend & ML
- ARCHITECTURE — Financial News Sentiment & Market Association System
- test_persistence.py
- FinNews: Financial News Sentiment & Market Association System
- NewsItem
- date
- SCHEMA — Data Contracts
- test_cli_commands.py
- AGENTS.md — Panduan untuk AI Agent Kolaborator
- ._parse
- ParquetStore
- Model Router: Cascade Routing ke Model Spesialis
- BaselineTfidfSentiment
- build_router_centroids.py
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
- frontend/GUI/ — Static ECharts HTML Dashboard (FR-15)
- graph.sh
- README.md
- __init__.py
- .get_active_universe
- .get_alloc_suggestions
- .load
- .latest_source_health
- .query_articles_by_target
- .query_stats
- .save_alloc_suggestion
- .save_labels
- find_skill_dirs
- .save_raw_articles
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
- .route_article
- .is_valid_target
- .save_article
- .save_daily_sentiment

## God Nodes (most connected - your core abstractions)
1. `Database` - 121 edges
2. `Pipeline` - 42 edges
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

## Communities (98 total, 26 thin omitted)

### Community 0 - "cli.py"
Cohesion: 0.05
Nodes (49): build_parser(), cmd_aggregate(), cmd_clean(), cmd_export(), cmd_pipeline(), cmd_prices(), cmd_report(), cmd_score() (+41 more)

### Community 1 - ".compute_ols_hac"
Cohesion: 0.07
Nodes (46): Any, DataFrame, date, Frame bersih: terurut tanggal, kolom `return`, tanpa baris kosong.          Sent, Aturan bandwidth Newey-West: floor(4 * (n/100) ** (2/9))., Regresi OLS `return ~ sentiment` dengan galat standar Newey-West (HAC)., Uji kausalitas Granger: apakah sentimen membantu memprediksi return.          Ar, Executes deterministic econometric tests between sentiment and market metrics. (+38 more)

### Community 2 - "DESIGN — Model, Scoring, Statistik & Antarmuka"
Cohesion: 0.04
Nodes (47): 10. Keterbatasan, 11.1 Kelas aset, 11.2 Skor per kelas (`alloc_map.yaml`), 11.3 Rumus, 11.4 Preset profil (contoh, bisa diubah; total wajib 100%), 11.5 Output, 11. Allocation Tilt, 12.1 Persona awal (`personas.yaml`) (+39 more)

### Community 3 - "app.js"
Cohesion: 0.11
Nodes (46): api(), applyNewsFilter(), bindControls(), bindPersonaButtons(), bindTabs(), demoImpacts(), demoQuality(), demoSeries() (+38 more)

### Community 4 - "PriceRecord"
Cohesion: 0.13
Nodes (17): Market data and news collectors., FetchResult, PriceCollector, PriceFetchError, date, Path, RuntimeError, Price data collector for the 3 core locked assets (XAU, RATE_UST, SPX).  Sumber (+9 more)

### Community 5 - "DailyQuota"
Cohesion: 0.08
Nodes (33): DailyQuota, Connection, Path, RuntimeError, QuotaExceeded, QuotaStatus, Penjaga kuota request harian — untuk sumber dengan batas 10–100 req/hari.  Menga, Baca pemakaian hari ini tanpa menambah apa pun. (+25 more)

### Community 6 - "ModelNotFittedError"
Cohesion: 0.14
Nodes (15): Tests for baseline ML model and evaluation metrics., Model tanpa fit()/load() harus melempar, bukan mengarang prior.      Sebelum per, fit() pada data kecil harus menghasilkan prediksi valid., Tests F1 macro, accuracy, and kappa computation., test_evaluation_metrics(), test_fit_membuat_model_siap(), test_model_belum_dilatih_melempar(), 01_baseline_exploration.py  Eksplorasi baseline model (M1: TF-IDF + Logistic Reg (+7 more)

### Community 7 - "HealthReport"
Cohesion: 0.16
Nodes (10): FinnhubAdapter, Any, Tarik berita relevan untuk satu target.          Menggabungkan beberapa kategori, ApiSpec, Path, Metadata satu penyedia API., Muat .env bila ada. Tidak melempar bila file tidak ditemukan., _specs() (+2 more)

### Community 8 - "news_cli.py"
Cohesion: 0.09
Nodes (32): datetime, Timestamp UTC timezone-aware — dipakai sebagai fetched_at., Konversi ke kontrak `RawArticle` (SCHEMA)., utcnow(), ApiRegistry, identify_apis(), Nama penyedia yang env var-nya kosong., Laporan kesehatan semua penyedia.          `probe=False` hanya memeriksa keberad (+24 more)

### Community 9 - "Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro"
Cohesion: 0.06
Nodes (31): 1.1 Masalah & Problem Statement, 1.2 Objektif, Metrik Domain, dan Metrik Teknis, 1.3 Uji Kecocokan Solusi (Component Necessity Test), 1. Problem Framing, 2.1 Tujuan Sistem, 2.2 Prinsip Desain, 2.3 Cakupan 3 Target Makro Terkunci (Murni 3 v2026-10-11-p3), 2. Deskripsi Sistem (+23 more)

### Community 10 - "Article"
Cohesion: 0.12
Nodes (21): ArticleCleaner, date, datetime, Normalization, deduplication, language detection, and time-alignment., Prepares raw incoming articles for pipeline consumption., Cleans whitespace, HTML tags, and non-printable characters., Generates sha256(norm(title)+norm(body))[:16] per SCHEMA., Simple heuristic language detector for ID vs EN. (+13 more)

### Community 11 - "test_dedup.py"
Cohesion: 0.11
Nodes (30): NearDuplicateDetector, Menandai artikel yang mirip dengan artikel lain via `duplicate_of`., _article(), pipeline_db(), Tests for T-6 / FR-2: near-duplicate detection.  Dedup sebelumnya hanya exact-ha, Dua rilis Fed berbeda pemohon punya kalimat nyaris sama.      Pada data nyata sk, Skor 0.55-0.85: dilaporkan, tidak digabung otomatis., Salin DB nyata bila ada, supaya uji memakai data sungguhan. (+22 more)

### Community 12 - "main"
Cohesion: 0.10
Nodes (29): main(), Dengan data minim, `stats` harus berhenti dengan pesan jelas (exit 0)., DB kosong: lewati tabel kosong, jangan menulis file palsu., test_export_on_empty_db_does_not_crash(), test_stats_reports_insufficient_pairs_without_crashing(), test_status_runs(), _count(), Path (+21 more)

### Community 13 - "ModelRouter"
Cohesion: 0.10
Nodes (25): ModelRouter, Path, Two-stage cascade router: news text -> specialist model id.  Tahap 1: petunjuk s, Lowercase token tanpa stopword. Dipakai builder dan router., Routes an article to the specialist model that should score it., Rata-rata z dan jumlah bukti kuat per domain., Returns (model_ids, reason, score). reason: source|keyword|log_odds|fallback., tokens() (+17 more)

### Community 14 - "AllocationEngine"
Cohesion: 0.09
Nodes (35): AllocationEngine, ProfileConfigError, Path, Deterministic Allocation Tilt engine satisfying strict 100% sum constraint., Derives scores for 6 allocation classes using alloc_map.yaml.         Score tupl, Calculates constrained allocation tilt for a specific profile.         Strictly, `alloc_profiles.yaml` melanggar invarian SCHEMA.md #10/#11., Computes relative portfolio tilt adjustments from asset scores. (+27 more)

### Community 15 - "ApiStatus"
Cohesion: 0.11
Nodes (22): Adapter Alpha Vantage NEWS_SENTIMENT.  Endpoint: GET /query?function=NEWS_SENTIM, ApiStatus, HealthReport, Any, Enum, str, Primitif bersama untuk seluruh adapter news API., Hasil identifikasi satu penyedia API. (+14 more)

### Community 16 - ".get_connection"
Cohesion: 0.06
Nodes (11): Dampak satu artikel pada satu aset, atau None bila tidak ada.          Dipakai e, Sumber yang SEDANG gagal `threshold` kali berturut-turut.          Hanya keadaan, Stores a TargetImpact record., Stores a daily asset price., Stores a raw (unnormalized) article. Returns raw_id.          Deduplikasi memaka, Bulk insert. Returns jumlah baris baru., Returns raw articles, terbaru dulu., Bulk insert normalized articles. Returns jumlah baris ditulis. (+3 more)

### Community 17 - "ApiError"
Cohesion: 0.18
Nodes (9): ApiError, Any, GET JSON dengan retry. Melempar `ApiError` setelah percobaan habis.          `he, GET teks mentah (untuk RSS/XML)., Kegagalan HTTP yang sudah diklasifikasi., test_api_error_carries_status(), test_client_masks_secrets_in_params(), Exception (+1 more)

### Community 18 - "test_news_api.py"
Cohesion: 0.09
Nodes (28): count_hits(), _load_registry(), matches_target(), _pattern(), Path, Kata kunci relevansi target — dibaca dari `data/source_registry.yaml`.  Registry, Jumlah kata kunci berbeda yang cocok di teks., Skor relevansi: 2x kata kunci target + 1x kata kunci makro.      Skor 0 berarti (+20 more)

### Community 19 - "test_source_registry.py"
Cohesion: 0.08
Nodes (22): _load_feeds(), Path, Baca `targets.<ID>.feeds` dari registry.      Hanya entri ber-`type: rss` yang d, T-4 / FR-3: registry YAML adalah satu-satunya sumber kebenaran.  Sebelum perbaik, Entri non-RSS (mis. deklarasi API) tidak boleh masuk daftar feed., Registry hilang: program tetap hidup, tetapi jujur soal sumbernya., Cadangan harus jauh lebih kecil dari registry asli.      Kalau cadangan sama pan, Regresi: pindah ke YAML tidak boleh mengurangi cakupan routing.      Daftar lama (+14 more)

### Community 20 - "test_news_horizon.py"
Cohesion: 0.06
Nodes (43): Basis, Direction, EvidenceSpan, TargetImpact, Queries recent target impacts., Target tagging and impact graph traversal., Router for mapping news text to targets via keywords and macro themes., Finds direct alias matches in text.         Returns list of (asset_id, matched_a (+35 more)

### Community 21 - "test_router_db_integration.py"
Cohesion: 0.10
Nodes (17): Path, Database, Queries recent econometric results for asset., Simpan AllocationSuggestion beserta seluruh barisnya.          `article_id` pada, Manages SQLite connections and queries for FInews., Bulk insert labels. Each dict: article_id, asset_id, annotator, label., Database and storage repository., db() (+9 more)

### Community 22 - "Dataset Card for Sentiment Analysis of Commodity News (Gold)"
Cohesion: 0.09
Nodes (22): Acknowledgements, Bias, Risks, and Limitations, Citation, Content, Context, Curation Rationale, Data Collection and Processing, Data Fields (+14 more)

### Community 23 - "ArticleSentiment"
Cohesion: 0.14
Nodes (16): ABC, ArticleSentiment, ModelProbs, test_save_sentiment_one_row_per_model(), Probabilities must sum to 1.0 within tolerance., test_model_probs_sum_to_one(), BaseModel, ModelNotFittedError (+8 more)

### Community 24 - "Pipeline"
Cohesion: 0.18
Nodes (17): _count(), db_path(), _iso(), datetime, Path, Test integrasi end-to-end: raw_articles -> articles -> impacts -> daily_sentimen, Menjalankan dua kali tidak boleh menggandakan baris., --dry-run menghitung tapi tidak menyentuh database. (+9 more)

### Community 25 - "adapters.py"
Cohesion: 0.20
Nodes (18): fomc_stance(), fomc_to_raw(), fomc_tone(), _gold_parse_date(), gold_to_raw(), gold_tone(), DataFrame, datetime (+10 more)

### Community 26 - "PipelineStats"
Cohesion: 0.12
Nodes (18): Pipeline, PipelineStats, Menyambungkan komponen-komponen menjadi satu alur berjalan., Mengisi asset_master & asset_aliases.          Tanpa ini `/api/universe` mengemb, Memuat model sentimen. Gagal keras bila tidak ada.          AUDIT K-4: lebih bai, raw_articles -> Article, lalu tulis ke tabel `articles`., Baca kembali `Article` dari tabel `articles`.          S-4: `cmd_score` dulu mem, Tandai near-duplicate terhadap riwayat DB dan sesama batch.          Artikel dup (+10 more)

### Community 27 - "PRD — Financial News Sentiment & Market Association System"
Cohesion: 0.10
Nodes (20): 10. Sumber Data (ringkas; detail di `ARCHITECTURE.md` §4), 11. Fase, 12. Risiko, 13. Open Questions, 14.1 Allocation Tilt, 14.2 Persona POV (5 persona), 14.3 Catatan Penting, 14. Fitur Tambahan (v0.3) (+12 more)

### Community 28 - "RULES — Aturan Wajib Proyek"
Cohesion: 0.10
Nodes (20): 10. Untuk AI Assistant yang Mengerjakan Repo Ini, 11.1 Aturan Frontend (GUI Web & TUI), 11. Aturan Allocation Tilt & Persona POV (v0.3), 1.1 Definisi, 1.2 `basis` dan batas confidence, 1.3 Evidence & rationale, 1.4 Target, 1.5 Disclaimer (+12 more)

### Community 29 - "Upgrade UI FInews"
Cohesion: 0.10
Nodes (20): 1. Tujuan, 2. Kondisi UI Saat Ini, 3.1 Adaptasi Splash Screen yang Sudah Ada, 3. Struktur Halaman yang Direkomendasikan, 4. Prioritas Upgrade, 5. Perubahan Kontrak Minimum, 6. Urutan Implementasi, 7. Yang Sengaja Tidak Dibuat (+12 more)

### Community 30 - "TargetImpact"
Cohesion: 0.09
Nodes (23): DailyAggregator, date, Aggregates article impacts into daily sentiment series., Computes daily mean and weighted sentiment per target., Aggregates impacts for a single asset on a given trading date.         Strict in, Aggregates batch of impacts, explicitly creating empty records         with scor, Daily sentiment aggregation across assets., DailySentiment (+15 more)

### Community 31 - "schema.py"
Cohesion: 0.24
Nodes (8): Deterministic statistical engine for sentiment-market association., _demo_daily_prices(), StatEngine multi-lag tests for the association workbench (Upgrade.md UI-05)., Deterministic series: news on even days, alternating score and close., Merged frame keeps engine columns; news-free days stay NaN, not 0., Live computation returns one result per lag 0..max_lag, metric=return., test_frame_keeps_news_free_days_nan(), test_spearman_lags_computed_live()

### Community 32 - "test_source_health.py"
Cohesion: 0.10
Nodes (12): db(), Tests for T-3: riwayat kesehatan sumber & alert (FR-18).  Yang diuji bukan sekad, Detail sangat panjang tidak boleh menggembungkan tabel tanpa batas., Satu-dua kegagalan belum boleh memicu alert., Setelah sumber pulih, alert harus berhenti -- bukan menyala selamanya., `no_key` adalah pilihan konfigurasi, bukan sumber yang mati., Pemeriksaan dalam detik yang sama tidak boleh menghasilkan baris ganda.      `ch, test_alert_clears_after_recovery() (+4 more)

### Community 33 - "EulerpoolAdapter"
Cohesion: 0.20
Nodes (10): EulerpoolAdapter, Any, datetime, Satu panggilan HTTP. Memesan kuota lebih dulu bila dijaga.          `limit` di-c, `datetime` dari Eulerpool berupa epoch detik (int)., Tolak berita lebih tua dari MAX_AGE_DAYS atau bertanggal masa depan., Cek kunci dengan satu request minimum (limit=1)., Tarik berita relevan untuk satu target.          Biaya kuota: **1 request**, ber (+2 more)

### Community 34 - "_latest_scores"
Cohesion: 0.20
Nodes (6): NewsAPIAdapter, Protocol, Tarik berita untuk satu target universe., Kontrak setiap adapter penyedia berita., True bila kredensial tersedia., Uji ringan: kunci valid? ada data?

### Community 35 - "ReportExporter"
Cohesion: 0.33
Nodes (8): load_split(), main(), _proba_matrix(), Path, Melatih baseline TF-IDF + LR dari dataset gold_sinha (nyata, berlabel).  Dataset, Membaca satu split parquet, mengembalikan (texts, labels)., Melatih dan menyimpan model. Mengembalikan metrik evaluasi., train()

### Community 36 - "db.py"
Cohesion: 0.14
Nodes (16): Tests for S-1: endpoint API tidak boleh menyajikan angka karangan.  Sebelum perb, Parameter eksplisit tetap boleh menimpa DB (untuk eksplorasi)., Skor dari DB harus memengaruhi hasil, bukan konstanta., Aset tanpa data harus ditandai `tanpa_data`, bukan diberi angka karangan., Regresi: 0.25/0.70 tidak boleh muncul lagi sebagai skor XAU., Batas keras RULES: total alokasi harus tetap 100%., Tanpa dampak tercatat, endpoint harus 404 -- bukan mengarang skor., Bila dampak ada, angka dari DB yang dipakai. (+8 more)

### Community 37 - "Database"
Cohesion: 0.12
Nodes (22): _clean(), Parse RSS 2.0 atau Atom menjadi list dict mentah., Buang tag HTML dan rapikan spasi., _article(), db(), Test untuk CRUD tabel berita (K-3) dan kolektor RSS., _raw(), test_get_missing_article_returns_none() (+14 more)

### Community 38 - "NewsHorizon"
Cohesion: 0.13
Nodes (22): PersonaEngine, Path, Deterministic Persona POV engine computing BUY/HOLD/SELL stances., Evaluates 5 investor personas stances for a given impact., Calculates decay/alignment between news horizon and persona horizon., Calculates stance for a specific persona based on parameters.         Determinis, Evaluates all 5 personas., Persona POV simulation engine. (+14 more)

### Community 39 - "Jalur Data — K-3 → A → C → B"
Cohesion: 0.12
Nodes (15): Batasan yang perlu diketahui, Feed terverifikasi hidup, Feed yang dibuang (jangan dipakai lagi), Identifikasi API, Jalur A — Harga, Jalur B — Berita via RSS, Jalur C — Berita via API, Jalur Data — K-3 → A → C → B (+7 more)

### Community 40 - "GUI THEME — Claude × Bloomberg"
Cohesion: 0.12
Nodes (15): 10. Tipografi (ringkas; versi font gratis padanan), 11. CSS Variables (siap salin), 12. Konfigurasi Streamlit (jika dipakai; cek dukungan font kustom pada versi yang dipakai), 13. Daftar Periksa Implementasi, 1. Konsep, 2. Warna Inti (dari spesifikasi), 3. Token Turunan — Sisi Terang, 4. Token Turunan — Sisi Gelap (Technical Surface) (+7 more)

### Community 41 - "TargetRouter"
Cohesion: 0.17
Nodes (14): Tests for T-5: ambang & kalibrasi router berasal dari YAML, bukan kode.  Alasan, Router yang membaca config dari tmp_path (bukan data/ asli)., Nilai bawaan harus identik dengan angka yang dulu ditanam di kode.      Kalau be, Plafon keyakinan makro tidak boleh terlampaui berapa pun bobotnya., Menaikkan ambang harus bisa memaksa arah menjadi NETRAL., YAML rusak tidak boleh membuat router mati total., _router(), test_broken_yaml_falls_back_to_defaults() (+6 more)

### Community 42 - "AUDIT v4 — Database, Backend & ML"
Cohesion: 0.13
Nodes (14): 1. FR-6 / K-3 · FinBERT XAU belum ada — **P0, satu-satunya yang kosong**, 2. FR-2 · near-duplicate tidak terbukti bekerja — **P0, ✅ SELESAI**, 3. FR-1 · ingest CSV/JSON/manual belum ada — **P0, parsial**, 4. FR-20 · tabel `alloc_profiles` mati — **P1, DITUNDA (keputusan pemilik)**, AUDIT v4 — Database, Backend & ML, Cakupan Test, Catatan Metodologi, Kenapa v4 ini ada (+6 more)

### Community 43 - "ARCHITECTURE — Financial News Sentiment & Market Association System"
Cohesion: 0.14
Nodes (13): 10. Kontrak Penyajian, 11. Modul Tambahan v0.3, 1. Gambaran Umum, 2. Lapisan, 3. Tahap Pipeline, 4. Sumber Data & Source Registry, 5. Orkestrasi, 6. Struktur Repo (+5 more)

### Community 44 - "test_persistence.py"
Cohesion: 0.09
Nodes (19): create_app(), _latest_scores(), Path, FastAPI REST application for FinNews., Ambil skor sentimen terakhir per aset dari DB.      Mengembalikan (scores, sourc, Creates and configures the FastAPI application., FastAPI REST application., client() (+11 more)

### Community 45 - "FinNews: Financial News Sentiment & Market Association System"
Cohesion: 0.15
Nodes (12): 1. Prasyarat & Instalasi, 2. Menjalankan Unit Test, 3. Eksplorasi Baseline Model (ML Offline), 4. Menjalankan Server API Backend, 🏛️ Arsitektur Sistem (3-Tier Layer), 🔒 Aturan Desain & Integritas Kuantitatif, FinNews: Financial News Sentiment & Market Association System, 🎯 Murni 3 Supervised (`XAU` / `RATE_UST` / `SPX`) (+4 more)

### Community 46 - "NewsItem"
Cohesion: 0.33
Nodes (6): AlphaVantageAdapter, Any, NewsItem, Satu berita mentah, belum dinormalisasi (belum punya article_id)., test_alphavantage_without_key_is_not_configured(), test_news_item_to_raw_article()

### Community 47 - "date"
Cohesion: 0.17
Nodes (6): date, Retrieves joint sentiment and price series for a target., Stores one article→target mapping., Bulk insert mappings untuk satu artikel. Returns jumlah baris., Queries daily sentiment records between dates., Queries price records between dates.

### Community 48 - "SCHEMA — Data Contracts"
Cohesion: 0.17
Nodes (11): 1. Enum, 2. Model Pipeline (Pydantic v2), 3. Output JSON (contoh), 4. Universe (`asset_master`), 5. Source Registry & Impact Graph, 6. Tabel Database (SQL), 7. Invarian (wajib dijaga validator), 8.1 Kontrak Role (+3 more)

### Community 49 - "test_cli_commands.py"
Cohesion: 0.21
Nodes (10): StatResult, SQLite database repository adhering to SCHEMA v0.5.0., Tests for T-2: CLI lengkap (FR-14) dan ekspor laporan.  Menekankan dua hal yang, `export` harus benar-benar memanggil ParquetStore dan menghasilkan file.      S-, Nilai harus selamat melewati Parquet, bukan hanya filenya ada., Regresi: laporan pernah mengabaikan argumen `stats` sepenuhnya., _stat(), test_export_command_writes_parquet() (+2 more)

### Community 50 - "AGENTS.md — Panduan untuk AI Agent Kolaborator"
Cohesion: 0.20
Nodes (9): 1. Mulai dari sini, bukan dari `ls -R`, 2. Peta cepat: di mana apa, 3. Aturan yang tidak boleh dilanggar, 4. Lingkup kerja per peran, 5. Perintah yang sering dipakai, 6. Konvensi commit, 7. Kondisi repository saat ini, 8. Saat ragu (+1 more)

### Community 51 - "._parse"
Cohesion: 0.33
Nodes (4): FeedStatus, Uji satu feed tanpa melempar., Kesehatan semua feed (atau hanya milik satu target)., Versi `HealthReport` agar seragam dengan adapter API.

### Community 52 - "ParquetStore"
Cohesion: 0.46
Nodes (3): MarketauxAdapter, Any, test_marketaux_without_key_is_not_configured()

### Community 53 - "Model Router: Cascade Routing ke Model Spesialis"
Cohesion: 0.20
Nodes (9): Arsitektur: dua tahap + fallback, Batasan yang diketahui, Cara menjalankan, Jejak audit, Masalah, Mengapa aturan bukti, bukan rata-rata, Model Router: Cascade Routing ke Model Spesialis, Tahap 1 — sumber dan kata kunci (+1 more)

### Community 54 - "BaselineTfidfSentiment"
Cohesion: 0.18
Nodes (6): BaselineTfidfSentiment, RuntimeError, 3-class probabilities. Melempar bila model belum dilatih., Scores a single article text and outputs ArticleSentiment., TF-IDF + Logistic Regression baseline for 3-class financial sentiment., Melatih baseline.          labels: 0 = negative, 1 = neutral, 2 = positive

### Community 55 - "build_router_centroids.py"
Cohesion: 0.25
Nodes (5): _compose(), FR-2 / T-6: deteksi artikel near-duplicate.  Dedup yang ada sebelumnya hanya *ex, Kembalikan daftar artikel dengan `duplicate_of` terisi bila perlu.          `his, Teks pembanding: judul diberi bobot lebih dengan cara diulang.      Badan berita, Matriks cosine similarity antar teks. Mengembalikan None bila kosong.

### Community 56 - ".seed_aliases"
Cohesion: 0.33
Nodes (3): Path, Seeds the 3 core locked assets from asset_master.csv., Seeds asset aliases from aliases.csv.

### Community 57 - "fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX)"
Cohesion: 0.33
Nodes (5): fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX), Kerangka, Kontrak, Tugas track ini (M3, M6), Yang belum ada

### Community 58 - "xau/ — Track FinBERT-EMAS (target XAU)"
Cohesion: 0.33
Nodes (5): Kerangka, Kontrak, Tugas track ini (M2, M6), xau/ — Track FinBERT-EMAS (target XAU), Yang belum ada

### Community 59 - ".init_schema"
Cohesion: 0.40
Nodes (3): Connection, Initializes tables and indexes, lalu migrasi kolom yang menyusul., Menambah kolom baru pada DB lama. Idempoten dan aman diulang.

### Community 60 - ".save_label"
Cohesion: 0.40
Nodes (3): datetime, Catat satu hasil pemeriksaan kesehatan sumber.          Mengembalikan jumlah keg, Stores one human annotation.

### Community 61 - "dataset/ — Katalog Data"
Cohesion: 0.40
Nodes (4): dataset/ — Katalog Data, Dihapus 2026-10-11, Mapping label (beku), Sitasi

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

### Community 74 - ".load"
Cohesion: 0.22
Nodes (7): Model nyata harus memberi sinyal berbeda untuk teks bullish vs bearish., test_model_terlatih_membedakan_arah(), Model terlatih harus memberi skor berbeda untuk teks berbeda.      Test ini meng, test_model_memuat_dan_memberi_sinyal_berbeda(), Path, Memuat model terlatih dari disk., Menyimpan model terlatih ke disk (joblib).

### Community 80 - "find_skill_dirs"
Cohesion: 0.38
Nodes (6): find_skill_dirs(), main(), patch_text(), Path, Semua direktori skill graphify yang terpasang., Terapkan semua perbaikan. Kembalikan (teks_baru, berubah).      Idempoten: blok

## Knowledge Gaps
- **237 isolated node(s):** `finews`, `graph.sh script`, `GRAPHIFY_OUT`, `1. Mulai dari sini, bukan dari `ls -R``, `2. Peta cepat: di mana apa` (+232 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **26 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `test_router_db_integration.py` to `cli.py`, `PriceRecord`, `news_cli.py`, `Article`, `test_dedup.py`, `main`, `ModelRouter`, `.get_connection`, `test_news_horizon.py`, `ArticleSentiment`, `Pipeline`, `PipelineStats`, `TargetImpact`, `test_source_health.py`, `db.py`, `Database`, `test_persistence.py`, `date`, `test_cli_commands.py`, `.seed_aliases`, `.init_schema`, `.save_label`, `.get_active_universe`, `.get_alloc_suggestions`, `.latest_source_health`, `.query_stats`, `.save_alloc_suggestion`, `.save_labels`, `.save_raw_articles`, `.is_valid_target`, `.save_article`, `.save_daily_sentiment`?**
  _High betweenness centrality (0.198) - this node is a cross-community bridge._
- **Why does `RawArticle` connect `Article` to `_latest_scores`, `Database`, `NewsHorizon`, `news_cli.py`, `NewsItem`, `ApiStatus`, `.get_connection`, `test_cli_commands.py`, `test_router_db_integration.py`, `ArticleSentiment`, `adapters.py`, `PipelineStats`?**
  _High betweenness centrality (0.051) - this node is a cross-community bridge._
- **Why does `BaselineTfidfSentiment` connect `BaselineTfidfSentiment` to `ReportExporter`, `ModelNotFittedError`, `NewsHorizon`, `Article`, `.load`, `ArticleSentiment`, `Pipeline`, `PipelineStats`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Database` (e.g. with `Pipeline` and `PipelineError`) actually correct?**
  _`Database` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Pipeline` (e.g. with `DailyAggregator` and `ArticleCleaner`) actually correct?**
  _`Pipeline` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ApiError` (e.g. with `AlphaVantageAdapter` and `ApiStatus`) actually correct?**
  _`ApiError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `TargetImpact` (e.g. with `DailyAggregator` and `Pipeline`) actually correct?**
  _`TargetImpact` has 6 INFERRED edges - model-reasoned connections that need verification._