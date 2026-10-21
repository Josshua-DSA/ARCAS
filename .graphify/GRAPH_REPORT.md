# Graph Report - .  (2026-10-21)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 1443 nodes · 2697 edges · 106 communities (73 shown, 33 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 167 edges (avg confidence: 0.52)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `cc145753`
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
- seeded_db
- .get_impact_for_article
- .is_valid_target
- .query_impacts
- .save_article
- .save_daily_sentiment
- .save_impact
- .save_raw_article
- .save_sentiment
- .sources_needing_alert
- __init__.py

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

## Communities (106 total, 33 thin omitted)

### Community 0 - "cli.py"
Cohesion: 0.14
Nodes (25): build_parser(), cmd_aggregate(), cmd_clean(), cmd_export(), cmd_pipeline(), cmd_prices(), cmd_report(), cmd_score() (+17 more)

### Community 1 - ".compute_ols_hac"
Cohesion: 0.06
Nodes (54): StatResult, Any, DataFrame, date, Frame bersih: terurut tanggal, kolom `return`, tanpa baris kosong.          Sent, Aturan bandwidth Newey-West: floor(4 * (n/100) ** (2/9))., Regresi OLS `return ~ sentiment` dengan galat standar Newey-West (HAC)., Uji kausalitas Granger: apakah sentimen membantu memprediksi return.          Ar (+46 more)

### Community 2 - "DESIGN — Model, Scoring, Statistik & Antarmuka"
Cohesion: 0.04
Nodes (47): 10. Keterbatasan, 11.1 Kelas aset, 11.2 Skor per kelas (`alloc_map.yaml`), 11.3 Rumus, 11.4 Preset profil (contoh, bisa diubah; total wajib 100%), 11.5 Output, 11. Allocation Tilt, 12.1 Persona awal (`personas.yaml`) (+39 more)

### Community 3 - "app.js"
Cohesion: 0.11
Nodes (46): api(), applyNewsFilter(), bindControls(), bindPersonaButtons(), bindTabs(), demoImpacts(), demoQuality(), demoSeries() (+38 more)

### Community 4 - "PriceRecord"
Cohesion: 0.07
Nodes (33): Market data and news collectors., FetchResult, PriceCollector, PriceFetchError, date, Path, RuntimeError, Price data collector for the 3 core locked assets (XAU, RATE_UST, SPX).  Sumber (+25 more)

### Community 5 - "DailyQuota"
Cohesion: 0.08
Nodes (33): DailyQuota, Connection, Path, RuntimeError, QuotaExceeded, QuotaStatus, Penjaga kuota request harian — untuk sumber dengan batas 10–100 req/hari.  Menga, Baca pemakaian hari ini tanpa menambah apa pun. (+25 more)

### Community 6 - "ModelNotFittedError"
Cohesion: 0.11
Nodes (19): Tests for baseline ML model and evaluation metrics., Model tanpa fit()/load() harus melempar, bukan mengarang prior.      Sebelum per, fit() pada data kecil harus menghasilkan prediksi valid., Tests F1 macro, accuracy, and kappa computation., test_evaluation_metrics(), test_fit_membuat_model_siap(), test_model_belum_dilatih_melempar(), 01_baseline_exploration.py  Eksplorasi baseline model (M1: TF-IDF + Logistic Reg (+11 more)

### Community 7 - "HealthReport"
Cohesion: 0.08
Nodes (26): HealthReport, NewsAPIAdapter, Any, Protocol, Ringkasan kesehatan satu penyedia API., Kontrak setiap adapter penyedia berita., True bila kredensial tersedia., Uji ringan: kunci valid? ada data? (+18 more)

### Community 8 - "news_cli.py"
Cohesion: 0.13
Nodes (24): datetime, Timestamp UTC timezone-aware — dipakai sebagai fetched_at., Konversi ke kontrak `RawArticle` (SCHEMA)., utcnow(), build_parser(), cmd_eulerpool(), cmd_fetch(), cmd_health() (+16 more)

### Community 9 - "Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro"
Cohesion: 0.06
Nodes (31): 1.1 Masalah & Problem Statement, 1.2 Objektif, Metrik Domain, dan Metrik Teknis, 1.3 Uji Kecocokan Solusi (Component Necessity Test), 1. Problem Framing, 2.1 Tujuan Sistem, 2.2 Prinsip Desain, 2.3 Cakupan 3 Target Makro Terkunci (Murni 3 v2026-10-11-p3), 2. Deskripsi Sistem (+23 more)

### Community 10 - "Article"
Cohesion: 0.11
Nodes (21): ArticleCleaner, date, datetime, Normalization, deduplication, language detection, and time-alignment., Prepares raw incoming articles for pipeline consumption., Cleans whitespace, HTML tags, and non-printable characters., Generates sha256(norm(title)+norm(body))[:16] per SCHEMA., Simple heuristic language detector for ID vs EN. (+13 more)

### Community 11 - "test_dedup.py"
Cohesion: 0.07
Nodes (41): _compose(), NearDuplicateDetector, FR-2 / T-6: deteksi artikel near-duplicate.  Dedup yang ada sebelumnya hanya *ex, Kembalikan daftar artikel dengan `duplicate_of` terisi bila perlu.          `his, Teks pembanding: judul diberi bobot lebih dengan cara diulang.      Badan berita, Menandai artikel yang mirip dengan artikel lain via `duplicate_of`., Matriks cosine similarity antar teks. Mengembalikan None bila kosong., _article() (+33 more)

### Community 12 - "main"
Cohesion: 0.16
Nodes (21): main(), _count(), S-4: test yang menyentuh jalur nyata, bukan hanya komponen terpisah.  AUDIT K-1, `score` sebelum `clean` harus menolak dengan pesan, bukan crash SQLite., Tahap 3: impacts -> daily_sentiment., Ketiga tahap berurutan menghasilkan data di semua tabel berita., S-5 lewat jalur nyata: horizon harus terisi, bukan NULL., Baris harian harus menunjuk aset yang benar, bukan placeholder. (+13 more)

### Community 13 - "ModelRouter"
Cohesion: 0.17
Nodes (15): ModelRouter, Path, Two-stage cascade router: news text -> specialist model id.  Tahap 1: petunjuk s, Routes an article to the specialist model that should score it., Tests for the two-stage cascade model router., Teks di luar domain tidak boleh dirutekan karena satu kata kebetulan., Uji cepat pada sampel dataset: akurasi rute harus tetap tinggi., router() (+7 more)

### Community 14 - "AllocationEngine"
Cohesion: 0.13
Nodes (18): AllocationEngine, Path, Deterministic Allocation Tilt engine satisfying strict 100% sum constraint., Computes relative portfolio tilt adjustments from asset scores., Derives scores for 6 allocation classes using alloc_map.yaml.         Score tupl, Calculates constrained allocation tilt for a specific profile.         Strictly, Allocation Tilt simulation engine., AllocationLine (+10 more)

### Community 15 - "ApiStatus"
Cohesion: 0.14
Nodes (17): Adapter Alpha Vantage NEWS_SENTIMENT.  Endpoint: GET /query?function=NEWS_SENTIM, ApiStatus, Enum, str, Primitif bersama untuk seluruh adapter news API., Hasil identifikasi satu penyedia API., env(), NewsAPIClient (+9 more)

### Community 16 - ".get_connection"
Cohesion: 0.08
Nodes (8): Stores econometric test result., Simpan PersonaView ke tabel `persona_views`.          NFR reproducibility: hasil, Baca kembali persona_views yang tersimpan (untuk audit)., Stores a daily asset price., Returns raw articles, terbaru dulu., Bulk insert normalized articles. Returns jumlah baris ditulis., Returns real provenance facts for GET /api/meta.          Everything comes from, Joins impacts with article metadata, session cut-off, and model probs.

### Community 17 - "ApiError"
Cohesion: 0.12
Nodes (14): ApiError, Any, GET JSON dengan retry. Melempar `ApiError` setelah percobaan habis.          `he, GET teks mentah (untuk RSS/XML)., Kegagalan HTTP yang sudah diklasifikasi., FinnhubAdapter, Any, Tarik berita relevan untuk satu target.          Menggabungkan beberapa kategori (+6 more)

### Community 18 - "test_news_api.py"
Cohesion: 0.09
Nodes (28): count_hits(), _load_registry(), matches_target(), _pattern(), Path, Kata kunci relevansi target — dibaca dari `data/source_registry.yaml`.  Registry, Jumlah kata kunci berbeda yang cocok di teks., Skor relevansi: 2x kata kunci target + 1x kata kunci makro.      Skor 0 berarti (+20 more)

### Community 19 - "test_source_registry.py"
Cohesion: 0.08
Nodes (22): _load_feeds(), Path, Baca `targets.<ID>.feeds` dari registry.      Hanya entri ber-`type: rss` yang d, T-4 / FR-3: registry YAML adalah satu-satunya sumber kebenaran.  Sebelum perbaik, Entri non-RSS (mis. deklarasi API) tidak boleh masuk daftar feed., Registry hilang: program tetap hidup, tetapi jujur soal sumbernya., Cadangan harus jauh lebih kecil dari registry asli.      Kalau cadangan sama pan, Regresi: pindah ke YAML tidak boleh mengurangi cakupan routing.      Daftar lama (+14 more)

### Community 20 - "test_news_horizon.py"
Cohesion: 0.09
Nodes (25): EvidenceSpan, Bila dampak ada, angka dari DB yang dipakai., test_persona_uses_recorded_impact(), db(), _impact(), S-5 / FR-23: `news_horizon` harus ditentukan, bukan konstanta.  Sebelum perbaika, S-5: horizon harus selamat melewati database.      Sebelumnya kolomnya tidak ada, DB lama (tanpa kolom) harus dimigrasi, bukan error. (+17 more)

### Community 21 - "test_router_db_integration.py"
Cohesion: 0.18
Nodes (10): Direction, Target tagging and impact graph traversal., Router for mapping news text to targets via keywords and macro themes., db(), Path, Integration test: routing decision tercatat di DB dan bisa dibaca kembali., Backward-compatible: tanpa router, kolom audit tetap kosong., test_impact_without_router_stays_null() (+2 more)

### Community 22 - "Dataset Card for Sentiment Analysis of Commodity News (Gold)"
Cohesion: 0.09
Nodes (22): Acknowledgements, Bias, Risks, and Limitations, Citation, Content, Context, Curation Rationale, Data Collection and Processing, Data Fields (+14 more)

### Community 23 - "ArticleSentiment"
Cohesion: 0.15
Nodes (13): ABC, ArticleSentiment, ModelProbs, test_save_sentiment_one_row_per_model(), Probabilities must sum to 1.0 within tolerance., test_model_probs_sum_to_one(), M1 Baseline Model: TF-IDF + Logistic Regression.  Kontrak penting (perbaikan AUD, BaseSentimentModel (+5 more)

### Community 24 - "Pipeline"
Cohesion: 0.18
Nodes (19): Pipeline, Menyambungkan komponen-komponen menjadi satu alur berjalan., _count(), db_path(), _iso(), datetime, Path, Test integrasi end-to-end: raw_articles -> articles -> impacts -> daily_sentimen (+11 more)

### Community 25 - "adapters.py"
Cohesion: 0.20
Nodes (18): fomc_stance(), fomc_to_raw(), fomc_tone(), _gold_parse_date(), gold_to_raw(), gold_tone(), DataFrame, datetime (+10 more)

### Community 26 - "PipelineStats"
Cohesion: 0.13
Nodes (12): Pipeline orkestrasi: menyambungkan komponen menjadi satu alur berjalan., PipelineError, PipelineStats, RuntimeError, Mengisi asset_master & asset_aliases.          Tanpa ini `/api/universe` mengemb, Memuat model sentimen. Gagal keras bila tidak ada.          AUDIT K-4: lebih bai, Sentimen + impact untuk tiap artikel., TargetImpact -> TargetTag, membawa basis & kutipan bukti. (+4 more)

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
Cohesion: 0.16
Nodes (14): DailyAggregator, date, Aggregates article impacts into daily sentiment series., Computes daily mean and weighted sentiment per target., Aggregates impacts for a single asset on a given trading date.         Strict in, Aggregates batch of impacts, explicitly creating empty records         with scor, Daily sentiment aggregation across assets., impacts -> daily_sentiment. (+6 more)

### Community 31 - "schema.py"
Cohesion: 0.27
Nodes (10): AssetClass, Basis, Enum, str, Data contracts and validation models (SCHEMA v0.6.0)., Stance, Tone, Track (+2 more)

### Community 32 - "test_source_health.py"
Cohesion: 0.10
Nodes (12): db(), Tests for T-3: riwayat kesehatan sumber & alert (FR-18).  Yang diuji bukan sekad, Detail sangat panjang tidak boleh menggembungkan tabel tanpa batas., Satu-dua kegagalan belum boleh memicu alert., Setelah sumber pulih, alert harus berhenti -- bukan menyala selamanya., `no_key` adalah pilihan konfigurasi, bukan sumber yang mati., Pemeriksaan dalam detik yang sama tidak boleh menghasilkan baris ganda.      `ch, test_alert_clears_after_recovery() (+4 more)

### Community 33 - "EulerpoolAdapter"
Cohesion: 0.20
Nodes (10): EulerpoolAdapter, Any, datetime, Satu panggilan HTTP. Memesan kuota lebih dulu bila dijaga.          `limit` di-c, `datetime` dari Eulerpool berupa epoch detik (int)., Tolak berita lebih tua dari MAX_AGE_DAYS atau bertanggal masa depan., Cek kunci dengan satu request minimum (limit=1)., Tarik berita relevan untuk satu target.          Biaya kuota: **1 request**, ber (+2 more)

### Community 35 - "ReportExporter"
Cohesion: 0.12
Nodes (14): Any, Path, Generates static HTML and JSON analytical reports into outputs/., Exports system analytical snapshots and statistics., Exports analytical JSON snapshot., Renders self-contained static HTML report for the 3 core targets., ReportExporter, Report export utilities. (+6 more)

### Community 36 - "db.py"
Cohesion: 0.10
Nodes (22): create_app(), Path, FastAPI REST application for FinNews., Creates and configures the FastAPI application., FastAPI REST application., SQLite database repository adhering to SCHEMA v0.5.0., client(), Tests for S-1: endpoint API tidak boleh menyajikan angka karangan.  Sebelum perb (+14 more)

### Community 37 - "Database"
Cohesion: 0.23
Nodes (18): Database, Manages SQLite connections and queries for FInews., _article(), db(), Test untuk CRUD tabel berita (K-3) dan kolektor RSS., _raw(), test_get_missing_article_returns_none(), test_query_articles_by_target_joins_articles() (+10 more)

### Community 38 - "NewsHorizon"
Cohesion: 0.14
Nodes (15): PersonaEngine, Path, Deterministic Persona POV engine computing BUY/HOLD/SELL stances., Evaluates 5 investor personas stances for a given impact., Calculates decay/alignment between news horizon and persona horizon., Calculates stance for a specific persona based on parameters.         Determinis, Evaluates all 5 personas., Persona POV simulation engine. (+7 more)

### Community 39 - "Jalur Data — K-3 → A → C → B"
Cohesion: 0.12
Nodes (15): Batasan yang perlu diketahui, Feed terverifikasi hidup, Feed yang dibuang (jangan dipakai lagi), Identifikasi API, Jalur A — Harga, Jalur B — Berita via RSS, Jalur C — Berita via API, Jalur Data — K-3 → A → C → B (+7 more)

### Community 40 - "GUI THEME — Claude × Bloomberg"
Cohesion: 0.12
Nodes (15): 10. Tipografi (ringkas; versi font gratis padanan), 11. CSS Variables (siap salin), 12. Konfigurasi Streamlit (jika dipakai; cek dukungan font kustom pada versi yang dipakai), 13. Daftar Periksa Implementasi, 1. Konsep, 2. Warna Inti (dari spesifikasi), 3. Token Turunan — Sisi Terang, 4. Token Turunan — Sisi Gelap (Technical Surface) (+7 more)

### Community 41 - "TargetRouter"
Cohesion: 0.13
Nodes (18): Path, Path, Tags targets and projects macro impact from text., TargetRouter, Tests for T-5: ambang & kalibrasi router berasal dari YAML, bukan kode.  Alasan, Router yang membaca config dari tmp_path (bukan data/ asli)., Nilai bawaan harus identik dengan angka yang dulu ditanam di kode.      Kalau be, Plafon keyakinan makro tidak boleh terlampaui berapa pun bobotnya. (+10 more)

### Community 42 - "AUDIT v4 — Database, Backend & ML"
Cohesion: 0.13
Nodes (14): 1. FR-6 / K-3 · FinBERT XAU belum ada — **P0, satu-satunya yang kosong**, 2. FR-2 · near-duplicate tidak terbukti bekerja — **P0, ✅ SELESAI**, 3. FR-1 · ingest CSV/JSON/manual belum ada — **P0, parsial**, 4. FR-20 · tabel `alloc_profiles` mati — **P1, kosmetik arsitektur**, AUDIT v4 — Database, Backend & ML, Cakupan Test, Catatan Metodologi, Kenapa v4 ini ada (+6 more)

### Community 43 - "ARCHITECTURE — Financial News Sentiment & Market Association System"
Cohesion: 0.14
Nodes (13): 10. Kontrak Penyajian, 11. Modul Tambahan v0.3, 1. Gambaran Umum, 2. Lapisan, 3. Tahap Pipeline, 4. Sumber Data & Source Registry, 5. Orkestrasi, 6. Struktur Repo (+5 more)

### Community 44 - "test_persistence.py"
Cohesion: 0.15
Nodes (9): Tests for S-2: persona_views & alloc_suggestions harus dipersistensi.  NFR repro, Audit butuh jejak: versi parameter dan waktu pembuatan., Yang disimpan harus sama dengan yang dikirim ke klien., Pemanggilan ulang harus menimpa, bukan menumpuk baris kembar., Tidak ada dampak -> tidak ada yang disimpan (jangan simpan karangan)., test_persisted_persona_matches_response(), test_persisted_rows_carry_provenance(), test_persona_not_stored_when_endpoint_404() (+1 more)

### Community 45 - "FinNews: Financial News Sentiment & Market Association System"
Cohesion: 0.15
Nodes (12): 1. Prasyarat & Instalasi, 2. Menjalankan Unit Test, 3. Eksplorasi Baseline Model (ML Offline), 4. Menjalankan Server API Backend, 🏛️ Arsitektur Sistem (3-Tier Layer), 🔒 Aturan Desain & Integritas Kuantitatif, FinNews: Financial News Sentiment & Market Association System, 🎯 Murni 3 Supervised (`XAU` / `RATE_UST` / `SPX`) (+4 more)

### Community 46 - "NewsItem"
Cohesion: 0.29
Nodes (6): AlphaVantageAdapter, Any, NewsItem, Tarik berita untuk satu target universe., Satu berita mentah, belum dinormalisasi (belum punya article_id)., test_news_item_to_raw_article()

### Community 47 - "date"
Cohesion: 0.17
Nodes (6): date, Retrieves joint sentiment and price series for a target., Stores one article→target mapping., Bulk insert mappings untuk satu artikel. Returns jumlah baris., Queries daily sentiment records between dates., Queries price records between dates.

### Community 48 - "SCHEMA — Data Contracts"
Cohesion: 0.17
Nodes (11): 1. Enum, 2. Model Pipeline (Pydantic v2), 3. Output JSON (contoh), 4. Universe (`asset_master`), 5. Source Registry & Impact Graph, 6. Tabel Database (SQL), 7. Invarian (wajib dijaga validator), 8.1 Kontrak Role (+3 more)

### Community 49 - "test_cli_commands.py"
Cohesion: 0.11
Nodes (18): db(), Tests for T-2: CLI lengkap (FR-14) dan ekspor laporan.  Menekankan dua hal yang, Dengan data minim, `stats` harus berhenti dengan pesan jelas (exit 0)., `export` harus benar-benar memanggil ParquetStore dan menghasilkan file.      S-, Nilai harus selamat melewati Parquet, bukan hanya filenya ada., DB kosong: lewati tabel kosong, jangan menulis file palsu., S-5 + S-3: horizon yang baru disimpan ikut terekspor., Semua perintah FR-14 harus terdaftar. (+10 more)

### Community 50 - "AGENTS.md — Panduan untuk AI Agent Kolaborator"
Cohesion: 0.20
Nodes (9): 1. Mulai dari sini, bukan dari `ls -R`, 2. Peta cepat: di mana apa, 3. Aturan yang tidak boleh dilanggar, 4. Lingkup kerja per peran, 5. Perintah yang sering dipakai, 6. Konvensi commit, 7. Kondisi repository saat ini, 8. Saat ragu (+1 more)

### Community 51 - "._parse"
Cohesion: 0.15
Nodes (10): _clean(), FeedStatus, Parse RSS 2.0 atau Atom menjadi list dict mentah., Uji satu feed tanpa melempar., Kesehatan semua feed (atau hanya milik satu target)., Versi `HealthReport` agar seragam dengan adapter API., Buang tag HTML dan rapikan spasi., test_rss_parse_atom() (+2 more)

### Community 52 - "ParquetStore"
Cohesion: 0.20
Nodes (8): ParquetStore, Any, DataFrame, Path, Parquet storage helpers for bulk dumps and training datasets., Manages Parquet writes and reads for processed time series., Saves records to a Parquet file., Reads records from a Parquet file.

### Community 53 - "Model Router: Cascade Routing ke Model Spesialis"
Cohesion: 0.20
Nodes (9): Arsitektur: dua tahap + fallback, Batasan yang diketahui, Cara menjalankan, Jejak audit, Masalah, Mengapa aturan bukti, bukan rata-rata, Model Router: Cascade Routing ke Model Spesialis, Tahap 1 — sumber dan kata kunci (+1 more)

### Community 54 - "BaselineTfidfSentiment"
Cohesion: 0.15
Nodes (12): BaselineTfidfSentiment, 3-class probabilities. Melempar bila model belum dilatih., Scores a single article text and outputs ArticleSentiment., TF-IDF + Logistic Regression baseline for 3-class financial sentiment., load_split(), main(), _proba_matrix(), Path (+4 more)

### Community 55 - "build_router_centroids.py"
Cohesion: 0.23
Nodes (9): Lowercase token tanpa stopword. Dipakai builder dan router., Rata-rata z dan jumlah bukti kuat per domain., Returns (model_ids, reason, score). reason: source|keyword|log_odds|fallback., tokens(), build(), counts(), load_docs(), main() (+1 more)

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

### Community 94 - ".route_article"
Cohesion: 0.33
Nodes (3): Finds direct alias matches in text.         Returns list of (asset_id, matched_a, Simple keyword detection for macro themes in text., Routes an article to target impacts via explicit mentions and macro themes.

### Community 95 - "seeded_db"
Cohesion: 0.67
Nodes (3): Path, Database dengan skema lengkap dan raw_articles siap olah., seeded_db()

## Knowledge Gaps
- **237 isolated node(s):** `finews`, `graph.sh script`, `GRAPHIFY_OUT`, `1. Mulai dari sini, bukan dari `ls -R``, `2. Peta cepat: di mana apa` (+232 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **33 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `cli.py`, `.compute_ols_hac`, `PriceRecord`, `news_cli.py`, `Article`, `test_dedup.py`, `main`, `.get_connection`, `test_news_horizon.py`, `test_router_db_integration.py`, `ArticleSentiment`, `Pipeline`, `PipelineStats`, `TargetImpact`, `schema.py`, `test_source_health.py`, `_latest_scores`, `db.py`, `TargetRouter`, `test_persistence.py`, `date`, `test_cli_commands.py`, `.seed_aliases`, `.init_schema`, `.save_label`, `.get_active_universe`, `.get_alloc_suggestions`, `.latest_source_health`, `.query_articles_by_target`, `.query_stats`, `.save_alloc_suggestion`, `.save_labels`, `.save_raw_articles`, `seeded_db`, `.get_impact_for_article`, `.is_valid_target`, `.query_impacts`, `.save_article`, `.save_daily_sentiment`, `.save_impact`, `.save_raw_article`, `.save_sentiment`, `.sources_needing_alert`, `__init__.py`?**
  _High betweenness centrality (0.189) - this node is a cross-community bridge._
- **Why does `RawArticle` connect `Article` to `db.py`, `Database`, `.save_raw_article`, `HealthReport`, `news_cli.py`, `NewsItem`, `ApiStatus`, `.save_raw_articles`, `Pipeline`, `adapters.py`, `PipelineStats`, `TargetImpact`, `schema.py`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `ApiError` connect `ApiError` to `EulerpoolAdapter`, `DailyQuota`, `Database`, `HealthReport`, `news_cli.py`, `NewsItem`, `ApiStatus`, `test_news_api.py`, `._parse`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Are the 15 inferred relationships involving `Database` (e.g. with `Pipeline` and `PipelineError`) actually correct?**
  _`Database` has 15 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `Pipeline` (e.g. with `DailyAggregator` and `ArticleCleaner`) actually correct?**
  _`Pipeline` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `ApiError` (e.g. with `AlphaVantageAdapter` and `ApiStatus`) actually correct?**
  _`ApiError` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `TargetImpact` (e.g. with `DailyAggregator` and `Pipeline`) actually correct?**
  _`TargetImpact` has 6 INFERRED edges - model-reasoned connections that need verification._