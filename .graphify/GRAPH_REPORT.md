# Graph Report - .  (2026-11-11)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 2849 nodes · 5335 edges · 179 communities (144 shown, 35 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 296 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d5c601ea`
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
- NewsItem
- news_cli.py
- Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro
- Lang
- test_dedup.py
- main
- ModelRouter
- AllocationEngine
- NewsAPIClient
- .get_connection
- ApiError
- test_news_api.py
- test_source_registry.py
- schema.py
- test_sim_decision_js.py
- Dataset Card for Sentiment Analysis of Commodity News (Gold)
- model.py
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
- validate
- app.py
- Database
- test_ingest_scheduler.py
- Jalur Data — K-3 → A → C → B
- GUI THEME — Claude × Bloomberg
- test_router_config.py
- test_news_preload.py
- ARCHITECTURE — Financial News Sentiment & Market Association System
- DailySentiment
- CONTRIBUTING.md — Panduan Kontribusi
- test_sim_api.py
- date
- SCHEMA — Data Contracts
- ReportExporter
- AGENTS.md — Panduan untuk AI Agent Kolaborator
- test_fomc_cache_recovery.py
- test_sim_service.py
- Model Router: Cascade Routing ke Model Spesialis
- Bagian II — Audit v2 (Delta)
- shell.js
- .seed_aliases
- xau/ — Track FinBERT-EMAS (target XAU)
- Connection
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
- test_effective_trading_date.py
- ModelNotFittedError
- neutral_band
- TargetRouter
- test_landing_page.py
- Article
- .save_persona_views
- find_skill_dirs
- test_schema_version.py
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
- PriceFetchError
- FinbertGoldSentiment
- sim_input.py
- evaluate_holdout.py
- .save_article
- .save_daily_sentiment
- test_fomc_track.py
- TestLabelContract
- test_xau_track.py
- IngestScheduler
- test_yfinance_collector.py
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
- StatEngine
- train_fomc_baseline
- 1. Aturan Domain
- simulations.js
- SimulationService
- TestTrainedModel
- 14. Fitur Tambahan (v0.3)
- 6. Panduan Menjalankan
- _load_registry
- seeded_db
- evidence.js
- 4. Tujuan & Non-Tujuan
- api.js
- .get_impact_for_article
- .query_articles_by_target
- test_stat_unique.py
- .save_price
- test_ingest_orphan_runs.py
- test_sim_state.py
- .compute_car_event_study
- compute_multiclass_ece
- TestBuildReport
- verify_local
- test_stats_engine.py
- TestDegradasiModelTerlihat
- test_persistence.py
- test_research_trace_js.py
- test_sim_readiness.py
- daily_headline.py
- news_preload.py
- test_evidence_pager_js.py
- softmax_with_temperature
- test_fade_guard_js.py
- compute_ece
- test_stat_replace.py
- backfill_news.py
- TestMcNemar
- test_overview_hero_json.py
- test_sim_chart_lifecycle.py
- test_metrics.py
- test_sim_card_ids.py
- Evaluasi Model ARCAS
- sim-decision.js
- conftest.py
- .benjamini_hochberg
- .hitung_hari_berpasangan
- .hash_text
- .claim_ingest_slot
- .finish_ingest_run
- .get_alloc_suggestions
- .get_persona_views
- .has_run_for_slot
- .is_valid_target
- .last_ingest_run
- .latest_source_health
- .query_impact_time_audit
- .save_articles
- .save_sentiment
- test_parser_has_all_expected_commands

## God Nodes (most connected - your core abstractions)
1. `Database` - 198 edges
2. `Pipeline` - 80 edges
3. `TargetRouter` - 70 edges
4. `Article` - 62 edges
5. `FOMCRoBERTaSentiment` - 46 edges
6. `ApiError` - 38 edges
7. `Lang` - 37 edges
8. `TargetImpact` - 37 edges
9. `NewsItem` - 35 edges
10. `RawArticle` - 35 edges

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

## Communities (179 total, 35 thin omitted)

### Community 0 - "cli.py"
Cohesion: 0.13
Nodes (29): build_parser(), cmd_aggregate(), cmd_check_schema(), cmd_clean(), cmd_export(), cmd_ingest(), cmd_pipeline(), cmd_prices() (+21 more)

### Community 1 - ".compute_ols_hac"
Cohesion: 0.11
Nodes (28): Regresi OLS `return ~ sentiment` dengan galat standar Newey-West (HAC)., Tests for T-1: OLS Newey-West HAC dan uji Granger (FR-11).  Fokus uji ini bukan, Di bawah ambang minimum, kembalikan kosong -- jangan mengarang hasil., Hari tanpa berita (score_mean NaN) harus dibuang, bukan diisi 0.      Kalau diis, Sentimen yang benar-benar memimpin return harus terdeteksi.      Hubungan dibuat, Kausalitas TERBALIK tidak boleh dilaporkan sebagai sentimen->return., `estimate` menyimpan F, sehingga tidak boleh negatif., Bangun (date, close, score_mean) dengan hubungan yang diketahui.      coef     : (+20 more)

### Community 2 - "DESIGN — Model, Scoring, Statistik & Antarmuka"
Cohesion: 0.04
Nodes (47): 10. Keterbatasan, 11.1 Kelas aset, 11.2 Skor per kelas (`alloc_map.yaml`), 11.3 Rumus, 11.4 Preset profil (contoh, bisa diubah; total wajib 100%), 11.5 Output, 11. Allocation Tilt, 12.1 Persona awal (`personas.yaml`) (+39 more)

### Community 3 - "test_manual_ingest.py"
Cohesion: 0.08
Nodes (49): _baca_csv(), baca_file(), _baca_json(), bangun_artikel(), _baris_ke_artikel(), HasilIngest, _normalisasi_kunci(), _parse_sentimen() (+41 more)

### Community 4 - ".fetch_prices"
Cohesion: 0.24
Nodes (6): date, Ambil harga nyata. Melempar `PriceFetchError` bila gagal.          Tidak ada fal, Seperti `fetch_prices`, tapi mengembalikan asal data secara eksplisit., Fetches real prices for all active core assets.          Satu aset gagal tidak m, Generates synthetic daily price series.          HANYA untuk test/offline simula, Ambil OHLC harian dari Yahoo chart API.          `period1`/`period2` memakai epo

### Community 5 - "DailyQuota"
Cohesion: 0.08
Nodes (33): DailyQuota, Connection, Path, RuntimeError, QuotaExceeded, QuotaStatus, Penjaga kuota request harian — untuk sumber dengan batas 10–100 req/hari.  Menga, Baca pemakaian hari ini tanpa menambah apa pun. (+25 more)

### Community 6 - "BaselineTfidfSentiment"
Cohesion: 0.12
Nodes (15): 01_baseline_exploration.py  Eksplorasi baseline model (M1: TF-IDF + Logistic Reg, Menjalankan pelatihan dan evaluasi baseline sentiment.     Labels: 0 = Negative,, run_experiment(), BaselineTfidfSentiment, 3-class probabilities. Melempar bila model belum dilatih., Scores a single article text and outputs ArticleSentiment., TF-IDF + Logistic Regression baseline for 3-class financial sentiment., load_split() (+7 more)

### Community 7 - "NewsItem"
Cohesion: 0.16
Nodes (11): AlphaVantageAdapter, Any, NewsItem, Satu berita mentah, belum dinormalisasi (belum punya article_id)., MarketauxAdapter, Any, ApiSpec, Path (+3 more)

### Community 8 - "news_cli.py"
Cohesion: 0.11
Nodes (24): datetime, Timestamp UTC timezone-aware — dipakai sebagai fetched_at., Konversi ke kontrak `RawArticle` (SCHEMA)., utcnow(), ApiRegistry, identify_apis(), Nama penyedia yang punya kredensial di env., Nama penyedia yang env var-nya kosong. (+16 more)

### Community 9 - "Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro"
Cohesion: 0.06
Nodes (31): 1.1 Masalah & Problem Statement, 1.2 Objektif, Metrik Domain, dan Metrik Teknis, 1.3 Uji Kecocokan Solusi (Component Necessity Test), 1. Problem Framing, 2.1 Tujuan Sistem, 2.2 Prinsip Desain, 2.3 Cakupan 3 Target Makro Terkunci (Murni 3 v2026-10-11-p3), 2. Deskripsi Sistem (+23 more)

### Community 10 - "Lang"
Cohesion: 0.05
Nodes (47): ArticleCleaner, Any, date, datetime, Normalization, deduplication, language detection, and time-alignment., Aligns published datetime to the correct trading date.         Rule: News publis, Prepares raw incoming articles for pipeline consumption., Transforms a RawArticle into a normalized Article contract. (+39 more)

### Community 11 - "test_dedup.py"
Cohesion: 0.07
Nodes (40): _compose(), NearDuplicateDetector, FR-2 / T-6: deteksi artikel near-duplicate.  Dedup yang ada sebelumnya hanya *ex, Kembalikan daftar artikel dengan `duplicate_of` terisi bila perlu.          `his, Teks pembanding: judul diberi bobot lebih dengan cara diulang.      Badan berita, Menandai artikel yang mirip dengan artikel lain via `duplicate_of`., Matriks cosine similarity antar teks. Mengembalikan None bila kosong., _article() (+32 more)

### Community 12 - "main"
Cohesion: 0.12
Nodes (26): main(), Dengan data minim, `stats` harus berhenti dengan pesan jelas (exit 0)., DB kosong: lewati tabel kosong, jangan menulis file palsu., test_export_on_empty_db_does_not_crash(), test_stats_reports_insufficient_pairs_without_crashing(), test_status_runs(), _count(), S-4: test yang menyentuh jalur nyata, bukan hanya komponen terpisah.  AUDIT K-1 (+18 more)

### Community 13 - "ModelRouter"
Cohesion: 0.07
Nodes (35): Muat model yang tersedia tanpa memproses teks apa pun.          Dipanggil dari l, ModelRouter, Path, Two-stage cascade router: news text -> specialist model id.  Tahap 1: petunjuk s, Lowercase token tanpa stopword. Dipakai builder dan router., Routes an article to the specialist model that should score it., Rata-rata z dan jumlah bukti kuat per domain., Returns (model_ids, reason, score). reason: source|keyword|log_odds|fallback. (+27 more)

### Community 14 - "AllocationEngine"
Cohesion: 0.06
Nodes (50): AllocationEngine, ProfileConfigError, Path, ValueError, Deterministic Allocation Tilt engine satisfying strict 100% sum constraint., Derives scores for 6 allocation classes using alloc_map.yaml.         Score tupl, Calculates constrained allocation tilt for a specific profile.         Strictly, `alloc_profiles.yaml` melanggar invarian SCHEMA.md #10/#11. (+42 more)

### Community 15 - "NewsAPIClient"
Cohesion: 0.11
Nodes (23): Adapter Alpha Vantage NEWS_SENTIMENT.  Endpoint: GET /query?function=NEWS_SENTIM, ApiStatus, HealthReport, Any, Enum, str, Primitif bersama untuk seluruh adapter news API., Hasil identifikasi satu penyedia API. (+15 more)

### Community 16 - ".get_connection"
Cohesion: 0.05
Nodes (14): Bulk insert labels. Each dict: article_id, asset_id, annotator, label., Returns real provenance facts for GET /api/meta.          Everything comes from, Ganti seluruh hasil statistik satu aset dengan `results`.          `save_stat` m, Queries recent econometric results for asset., Simpan AllocationSuggestion beserta seluruh barisnya.          `article_id` pada, Sumber yang SEDANG gagal `threshold` kali berturut-turut.          Hanya keadaan, Ambil satu jejak simulasi. None bila tidak ada (bukan galat)., Tutup run ingest yang ditinggal proses mati. Kembalikan jumlah baris.          P (+6 more)

### Community 17 - "ApiError"
Cohesion: 0.08
Nodes (23): ApiError, Any, Exception, GET JSON dengan retry. Melempar `ApiError` setelah percobaan habis.          `he, GET teks mentah (untuk RSS/XML)., Kegagalan HTTP yang sudah diklasifikasi., _clean(), FeedStatus (+15 more)

### Community 18 - "test_news_api.py"
Cohesion: 0.09
Nodes (27): FinnhubAdapter, Any, Tarik berita relevan untuk satu target.          Menggabungkan beberapa kategori, count_hits(), matches_target(), _pattern(), Jumlah kata kunci berbeda yang cocok di teks., Skor relevansi: 2x kata kunci target + 1x kata kunci makro.      Skor 0 berarti (+19 more)

### Community 19 - "test_source_registry.py"
Cohesion: 0.08
Nodes (22): _load_feeds(), Path, Baca `targets.<ID>.feeds` dari registry.      Hanya entri ber-`type: rss` yang d, T-4 / FR-3: registry YAML adalah satu-satunya sumber kebenaran.  Sebelum perbaik, Entri non-RSS (mis. deklarasi API) tidak boleh masuk daftar feed., Registry hilang: program tetap hidup, tetapi jujur soal sumbernya., Cadangan harus jauh lebih kecil dari registry asli.      Kalau cadangan sama pan, Regresi: pindah ke YAML tidak boleh mengurangi cakupan routing.      Daftar lama (+14 more)

### Community 20 - "schema.py"
Cohesion: 0.05
Nodes (61): AssetClass, Basis, Direction, EvidenceSpan, NewsHorizon, Enum, str, Data contracts and validation models (SCHEMA v0.6.0). (+53 more)

### Community 21 - "test_sim_decision_js.py"
Cohesion: 0.08
Nodes (45): _harga(), _harga_bursa(), _jalan(), _jalan_bukti(), _jalan_keputusan(), _jalan_rapikan(), Uji agregasi stance di klien tanpa browser.  Fungsi ini menentukan keputusan yan, Harga naik monoton: setiap kejadian bersentimen positif adalah 'kena'. (+37 more)

### Community 22 - "Dataset Card for Sentiment Analysis of Commodity News (Gold)"
Cohesion: 0.09
Nodes (22): Acknowledgements, Bias, Risks, and Limitations, Citation, Content, Context, Curation Rationale, Data Collection and Processing, Data Fields (+14 more)

### Community 23 - "model.py"
Cohesion: 0.15
Nodes (10): ABC, Tone, M1 Baseline Model: TF-IDF + Logistic Regression.  Kontrak penting (perbaikan AUD, BaseSentimentModel, Abstract base protocol for sentiment inference models., Protocol for financial sentiment classifiers., Name of the model architecture., Returns 3-class probabilities [p_pos, p_neu, p_neg] summing to 1.0. (+2 more)

### Community 24 - "test_pipeline_integration.py"
Cohesion: 0.18
Nodes (17): _count(), db_path(), _iso(), datetime, Path, Test integrasi end-to-end: raw_articles -> articles -> impacts -> daily_sentimen, Menjalankan dua kali tidak boleh menggandakan baris., --dry-run menghitung tapi tidak menyentuh database. (+9 more)

### Community 25 - "adapters.py"
Cohesion: 0.20
Nodes (18): fomc_stance(), fomc_to_raw(), fomc_tone(), _gold_parse_date(), gold_to_raw(), gold_tone(), DataFrame, datetime (+10 more)

### Community 26 - "Pipeline"
Cohesion: 0.07
Nodes (32): Pipeline, Any, Path, Menyambungkan komponen-komponen menjadi satu alur berjalan., Mengisi asset_master & asset_aliases.          Tanpa ini `/api/universe` mengemb, Memuat model spesialis FinBERT-EMAS secara lazy (FR-6).          Mengembalikan `, Memuat model spesialis FOMC-RoBERTa secara lazy.          Audit P1-1: kegagalan, Catat bahwa pipeline berjalan dengan model yang lebih lemah.          Degradasi (+24 more)

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
Cohesion: 0.11
Nodes (15): Tests for SQLite database initialization, seeding, and operations., Verifies that asset_master and aliases are properly seeded., Alias yang membingungkan tidak boleh kembali., Jejak lebih tua dari retensi dihapus; yang baru dipertahankan., get_meta_summary returns real counts and version stamps for /api/meta., Time audit join degrades to real empties, never fake timestamps., Tests saving and querying daily sentiments., `init_schema()` aman dipanggil berulang — sifat yang tadinya     tersembunyi di (+7 more)

### Community 31 - "test_news_cli.py"
Cohesion: 0.09
Nodes (37): build_parser(), _dedupe(), main(), _print_alerts(), ArgumentParser, Buang duplikat lintas penyedia berdasarkan judul ternormalisasi., Simpan hasil pemeriksaan ke `source_health` dan kembalikan daftar alert.      Di, _record_health() (+29 more)

### Community 32 - "test_source_health.py"
Cohesion: 0.10
Nodes (12): db(), Tests for T-3: riwayat kesehatan sumber & alert (FR-18).  Yang diuji bukan sekad, Detail sangat panjang tidak boleh menggembungkan tabel tanpa batas., Satu-dua kegagalan belum boleh memicu alert., Setelah sumber pulih, alert harus berhenti -- bukan menyala selamanya., `no_key` adalah pilihan konfigurasi, bukan sumber yang mati., Pemeriksaan dalam detik yang sama tidak boleh menghasilkan baris ganda.      `ch, test_alert_clears_after_recovery() (+4 more)

### Community 33 - "EulerpoolAdapter"
Cohesion: 0.20
Nodes (10): EulerpoolAdapter, Any, datetime, Satu panggilan HTTP. Memesan kuota lebih dulu bila dijaga.          `limit` di-c, `datetime` dari Eulerpool berupa epoch detik (int)., Tolak berita lebih tua dari MAX_AGE_DAYS atau bertanggal masa depan., Cek kunci dengan satu request minimum (limit=1)., Tarik berita relevan untuk satu target.          Biaya kuota: **1 request**, ber (+2 more)

### Community 34 - "NewsAPIAdapter"
Cohesion: 0.20
Nodes (6): NewsAPIAdapter, Protocol, Tarik berita untuk satu target universe., Kontrak setiap adapter penyedia berita., True bila kredensial tersedia., Uji ringan: kunci valid? ada data?

### Community 35 - "validate"
Cohesion: 0.09
Nodes (41): confidence_penalty(), InputRejected, ValueError, Input bukan berita/rumor. Pesannya siap ditampilkan ke pengguna., Validasi input. Melempar `InputRejected` bila bukan berita/rumor.      Aturannya, Faktor pengali keyakinan untuk rumor.      Rumor yang jelas ditandai sebagai rum, validate(), Uji gerbang input: hanya berita/rumor yang boleh lolos.  Kasus uji diambil dari (+33 more)

### Community 36 - "app.py"
Cohesion: 0.09
Nodes (22): create_app(), _latest_scores(), Path, FastAPI REST application for FinNews., Ambil skor sentimen terakhir per aset dari DB.      Mengembalikan (scores, sourc, Creates and configures the FastAPI application., FastAPI REST application., make_job() (+14 more)

### Community 37 - "Database"
Cohesion: 0.13
Nodes (27): Database, Manages SQLite connections and queries for FInews., Database and storage repository., db(), _article(), db(), Test untuk CRUD tabel berita (K-3) dan kolektor RSS., _raw() (+19 more)

### Community 38 - "test_ingest_scheduler.py"
Cohesion: 0.10
Nodes (37): next_slot(), Slot 07:00 WIB yang berlaku untuk `moment` (zona waktu apa pun).      Bila `mome, Slot 07:00 WIB berikutnya yang masih di masa depan., slot_for(), datetime, Uji penjadwal preload 07:00 WIB.  Fokus pada perilaku yang mudah salah dan mahal, Run gagal tidak menandai slot selesai: percobaan berikutnya mengulang., Tick tepat pukul 07:00 dianggap run terjadwal, bukan kejar. (+29 more)

### Community 39 - "Jalur Data — K-3 → A → C → B"
Cohesion: 0.12
Nodes (15): Batasan yang perlu diketahui, Feed terverifikasi hidup, Feed yang dibuang (jangan dipakai lagi), Identifikasi API, Jalur A — Harga, Jalur B — Berita via RSS, Jalur C — Berita via API, Jalur Data — K-3 → A → C → B (+7 more)

### Community 40 - "GUI THEME — Claude × Bloomberg"
Cohesion: 0.12
Nodes (15): 10. Tipografi (ringkas; versi font gratis padanan), 11. CSS Variables (siap salin), 12. Konfigurasi Streamlit (jika dipakai; cek dukungan font kustom pada versi yang dipakai), 13. Daftar Periksa Implementasi, 1. Konsep, 2. Warna Inti (dari spesifikasi), 3. Token Turunan — Sisi Terang, 4. Token Turunan — Sisi Gelap (Technical Surface) (+7 more)

### Community 41 - "test_router_config.py"
Cohesion: 0.17
Nodes (14): Tests for T-5: ambang & kalibrasi router berasal dari YAML, bukan kode.  Alasan, Router yang membaca config dari tmp_path (bukan data/ asli)., Nilai bawaan harus identik dengan angka yang dulu ditanam di kode.      Kalau be, Plafon keyakinan makro tidak boleh terlampaui berapa pun bobotnya., Menaikkan ambang harus bisa memaksa arah menjadi NETRAL., YAML rusak tidak boleh membuat router mati total., _router(), test_broken_yaml_falls_back_to_defaults() (+6 more)

### Community 42 - "test_news_preload.py"
Cohesion: 0.09
Nodes (32): _hit(), Uji `run_preload` tanpa menyentuh jaringan atau eulerpool sungguhan.  Yang dijag, Jalankan run_preload dan laporkan berapa kali eulerpool DITARIK., Inti P1-8: slot yang SEDANG dipegang proses lain harus DILEWATI.      Skenario a, Uji atomisitas sesungguhnya: N proses berebut slot yang sama.      Satu-satunya, Klaim hanya mengunci SLOT yang sama, bukan seluruh tabel., Proses yang mati di tengah jalan tidak boleh mengunci slot selamanya., `start_ingest_run` tetap tersedia untuk run manual yang berdampingan. (+24 more)

### Community 43 - "ARCHITECTURE — Financial News Sentiment & Market Association System"
Cohesion: 0.14
Nodes (13): 10. Kontrak Penyajian, 11. Modul Tambahan v0.3, 1. Gambaran Umum, 2. Lapisan, 3. Tahap Pipeline, 4. Sumber Data & Source Registry, 5. Orkestrasi, 6. Struktur Repo (+5 more)

### Community 44 - "DailySentiment"
Cohesion: 0.07
Nodes (30): DailyAggregator, date, Aggregates article impacts into daily sentiment series., Computes daily mean and weighted sentiment per target., Aggregates impacts for a single asset on a given trading date.         Strict in, Aggregates batch of impacts, explicitly creating empty records         with scor, Daily sentiment aggregation across assets., impacts -> daily_sentiment. (+22 more)

### Community 45 - "CONTRIBUTING.md — Panduan Kontribusi"
Cohesion: 0.06
Nodes (29): 10. Sebelum membuka Pull Request, 1. Prasyarat, 2. Setup, 3. Verifikasi sebelum commit, 4. Konvensi commit, 5. Aturan yang tidak boleh dilanggar, 6. Kalau mypy gagal karena numpy, 7. Code graph (`.graphify/`) (+21 more)

### Community 46 - "test_sim_api.py"
Cohesion: 0.07
Nodes (17): client(), Uji endpoint /api/simulate: gerbang, kontrak respons, dan penolakan., Target di luar 3 aset terkunci harus DITOLAK, bukan jadi "netral".      Regresi:, `xau` tetap diterima, tetapi respons memakai ejaan resmi `XAU`., Yang dibaca kembali harus angka yang TERSIMPAN, bukan hitung ulang., Hash harus deterministik dan tahan perbedaan spasi., Input yang ditolak gerbang tidak boleh meninggalkan baris jejak., Satu jalur DB per modul tes, dipakai `client` dan tes yang buka langsung. (+9 more)

### Community 47 - "date"
Cohesion: 0.17
Nodes (6): date, Stores one article→target mapping., Bulk insert mappings untuk satu artikel. Returns jumlah baris.          Setiap t, Queries daily sentiment records between dates., Queries price records between dates., Retrieves joint sentiment and price series for a target.

### Community 48 - "SCHEMA — Data Contracts"
Cohesion: 0.14
Nodes (13): 1. Enum, 2. Model Pipeline (Pydantic v2), 3. Output JSON (contoh), 4. Universe (`asset_master`), 5. Source Registry & Impact Graph, 6.1 Operasional Ingest & Kesehatan Sumber (v0.8.0), 6.1 Versi & Migrasi Skema (P3-5), 6. Tabel Database (SQL) (+5 more)

### Community 49 - "ReportExporter"
Cohesion: 0.10
Nodes (17): Any, Path, Generates static HTML and JSON analytical reports into outputs/., Exports system analytical snapshots and statistics., Exports analytical JSON snapshot., Renders self-contained static HTML report for the 3 core targets., ReportExporter, Report export utilities. (+9 more)

### Community 50 - "AGENTS.md — Panduan untuk AI Agent Kolaborator"
Cohesion: 0.20
Nodes (9): 1. Mulai dari sini, bukan dari `ls -R`, 2. Peta cepat: di mana apa, 3. Aturan yang tidak boleh dilanggar, 4. Lingkup kerja per peran, 5. Perintah yang sering dipakai, 6. Konvensi commit, 7. Kondisi repository saat ini, 8. Saat ragu (+1 more)

### Community 51 - "test_fomc_cache_recovery.py"
Cohesion: 0.09
Nodes (20): mod(), Dokumen evaluasi tidak boleh mengarang angka saat artefak tidak ada.  Aturan pro, Tes untuk pemulihan checkpoint FOMC-RoBERTa yang rusak di cache.  Gejala aslinya, Percobaan ulang maksimal sekali per checkpoint, bukan tak terbatas., Galat gated (401) bukan urusan cache; jangan hapus berkas apa pun., Berkas sah tidak boleh ikut terhapus., Sisa cache dibersihkan lalu muat ulang; hasilnya model terpakai., Bila tidak ada yang bisa dibersihkan, jangan buang waktu mengulang. (+12 more)

### Community 52 - "test_sim_service.py"
Cohesion: 0.08
Nodes (13): Uji simulasi end-to-end dengan model sungguhan.  Uji ini memuat bobot FinBERT-EM, Peringatan sumber hanya relevan untuk rumor., Bila FOMC gagal dimuat, itu harus terlihat, bukan disembunyikan., Skor FOMC positif = hawkish = emas turun. Ini bukan bug., Satu service harus bisa melayani dua domain tanpa saling mencemari., Penolakan harus terjadi sebelum model dimuat.      Service baru tanpa model: bil, Bukti utama bahwa bobot benar-benar dipakai.      Bila model diabaikan dan skor, test_berita_fed_hawkish_berarti_emas_bearish() (+5 more)

### Community 53 - "Model Router: Cascade Routing ke Model Spesialis"
Cohesion: 0.20
Nodes (9): Arsitektur: dua tahap + fallback, Batasan yang diketahui, Cara menjalankan, Jejak audit, Masalah, Mengapa aturan bukti, bukan rata-rata, Model Router: Cascade Routing ke Model Spesialis, Tahap 1 — sumber dan kata kunci (+1 more)

### Community 54 - "Bagian II — Audit v2 (Delta)"
Cohesion: 0.04
Nodes (48): 0. Ringkasan, 1. Temuan Kritis (P0), 2. Temuan Penting (P1), 3. Temuan Sedang (P2), 4. Temuan Ringan (P3), 5. Yang Sudah Baik (jangan diubah), 6. Prioritas Perbaikan, 7. Cara Mereproduksi Audit Ini (+40 more)

### Community 55 - "shell.js"
Cohesion: 0.17
Nodes (12): bindTabs(), esc(), fadeLalu(), fmt(), num(), pct(), renderPersona(), renderTabs() (+4 more)

### Community 56 - ".seed_aliases"
Cohesion: 0.33
Nodes (3): Path, Seeds the 3 core locked assets from asset_master.csv., Seeds asset aliases from aliases.csv.

### Community 58 - "xau/ — Track FinBERT-EMAS (target XAU)"
Cohesion: 0.18
Nodes (10): Artefak: tidak di-commit, Cara pakai, Catatan lingkungan (penting sebelum menjalankan training), Catatan teknis yang mudah salah, Kerangka, Keterbatasan, Kontrak, Sumber data (jujur, bukan sesuai nama folder) (+2 more)

### Community 59 - "Connection"
Cohesion: 0.14
Nodes (9): Connection, Initializes tables and indexes, lalu migrasi kolom yang menyusul.          Uruta, Baca versi skema DB dari `PRAGMA user_version`.          Sengaja TIDAK menebak d, Daftar kolom yang hilang, tanpa mengubah apa pun.          Dipakai `fi check-sch, Tambahkan satu kolom bila belum ada. True bila benar-benar ditambah., Lengkapi kolom yang hilang pada tabel yang sudah ada.          Idempoten dan ama, Hapus baris `stat_results` yang menyatakan bukti yang sama.          Menyisakan, Isi baris wajib bila belum ada. Tidak pernah menimpa data pengguna. (+1 more)

### Community 60 - ".save_label"
Cohesion: 0.40
Nodes (3): datetime, Stores one human annotation., Catat satu hasil pemeriksaan kesehatan sumber.          Mengembalikan jumlah keg

### Community 61 - "dataset/ — Katalog Data"
Cohesion: 0.40
Nodes (4): dataset/ — Katalog Data, Dihapus 2026-10-11, Mapping label (beku), Sitasi

### Community 62 - "splash.js"
Cohesion: 0.36
Nodes (6): jadwalkanBaris(), markAllDone(), stamp(), status(), tryFinish(), tulisBaris()

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

### Community 73 - "test_effective_trading_date.py"
Cohesion: 0.12
Nodes (19): TargetImpact -> TargetTag, membawa basis & kutipan bukti., BaseModel, TargetTag, db(), Tanggal bursa harus terisi untuk SETIAP aset yang ditandai, bukan hanya query_ta, Aset yang tidak ada di peta tanggal harus ditolak, bukan disimpan NULL.      Ini, query_target=SPX, tapi artikel juga menandai XAU dan RATE_UST., Sumber RSS tidak punya query_target; dulu peta tanggal kosong total. (+11 more)

### Community 74 - "ModelNotFittedError"
Cohesion: 0.11
Nodes (16): Tests for baseline ML model and evaluation metrics., Model tanpa fit()/load() harus melempar, bukan mengarang prior.      Sebelum per, fit() pada data kecil harus menghasilkan prediksi valid., Model nyata harus memberi sinyal berbeda untuk teks bullish vs bearish., test_fit_membuat_model_siap(), test_model_belum_dilatih_melempar(), test_model_terlatih_membedakan_arah(), Model terlatih harus memberi skor berbeda untuk teks berbeda.      Test ini meng (+8 more)

### Community 75 - "neutral_band"
Cohesion: 0.12
Nodes (20): XAU harus ada di peta arah; sebelumnya hanya RATE_UST/SPX., Path, RULES.md: ambang wajib di config, dan berkasnya harus konsisten., Berkas hilang tidak boleh mematikan model; dipakai nilai bawaan., `neutral_band` di luar [0, 1] diabaikan agar skor tidak selalu netral., test_ambang_netral_dari_config_bukan_literal(), test_ambang_netral_fallback_bila_config_hilang(), test_ambang_netral_menolak_nilai_tidak_masuk_akal() (+12 more)

### Community 76 - "TargetRouter"
Cohesion: 0.04
Nodes (51): Target tagging and impact graph traversal., _alias_pattern(), Path, Arah aset terhadap stance hawkish (+1/-1).          Aset yang tidak terdaftar di, Skor dalam ruang arah harga untuk satu aset.          Mode `price`: skor sudah b, Arah satu aset dari skor, tanpa perlu artikel menyebut aset itu.          Dipaka, Finds direct alias matches in text.         Returns list of (asset_id, matched_a, Kompilasi alias menjadi regex word-boundary, case-insensitive.      Spasi/tanda (+43 more)

### Community 77 - "test_landing_page.py"
Cohesion: 0.10
Nodes (18): _klien(), Halaman muka di akar, dasbor di /overview.html.  Akar `/` dulu menyajikan dasbor, Landing tidak boleh menyeret shell.js: ia memuat splash dan ticker., Angka cakupan hanya dari /api/meta; tidak ada angka mati di markup., Skip link wajib: nav 5 tautan berarti 5 Tab sebelum konten.      Tanpa ini pengg, Nav atas: Pricing, Documentation, Contribute. Tombol kepala ke dasbor., Halaman docs harus mencantumkan setiap route yang benar-benar ada.      Kalau ro, Tautan navigasi tidak boleh menunjuk localhost: pengunjung lain akan     kena ER (+10 more)

### Community 78 - "Article"
Cohesion: 0.09
Nodes (25): Article, Hasil validasi yang sudah bersih dan siap diproses., ValidatedInput, Endpoint simulasi: berita/rumor -> skor model -> stance persona.  Alur ini SENGA, Paragraf penjelas yang hanya memakai angka dari hasil perhitungan.      Tidak ad, Hasil lengkap satu analisis, siap dirender GUI., SimResult, SimStance (+17 more)

### Community 80 - "find_skill_dirs"
Cohesion: 0.38
Nodes (6): find_skill_dirs(), main(), patch_text(), Path, Semua direktori skill graphify yang terpasang., Terapkan semua perbaikan. Kembalikan (teks_baru, berubah).      Idempoten: blok

### Community 81 - "test_schema_version.py"
Cohesion: 0.13
Nodes (16): _db_lama(), Uji P3-5: versi skema, migrasi per-tabel, seed idempoten.  Masalah yang ditutup:, Inti P3-5: kolom di tabel LAIN juga harus ikut ditambahkan., Jaga agar peta migrasi tidak memuat kolom yang tidak pernah ada.      Tanpa tes, Bikin DB 'zaman dulu': tabel sudah ADA tapi belum punya kolom susulan.      Pent, `ON CONFLICT DO NOTHING`: data yang sudah ada tidak boleh ditimpa., `price_ticker` NOT NULL di DDL; seed tidak boleh mengirim None., DB yang belum pernah dimigrasi harus terbaca 0, bukan versi kode.      Ini regre (+8 more)

### Community 94 - "ArticleSentiment"
Cohesion: 0.11
Nodes (22): ArticleSentiment, ModelProbs, AUDIT v3 §2: duplikat tidak ikut diskor / menambah hitungan.      Memakai model, test_duplicate_does_not_increase_daily_article_count(), _create_sample_article(), Test integrasi Pipeline Runner dengan Model Spesialis FOMC-RoBERTa (Track B).  M, Artikel FOMC dovish memicu tema rates_down dan menghasilkan dampak SPX, RATE_UST, Artikel emas / non-FOMC tidak menggunakan model FOMC. (+14 more)

### Community 95 - "PriceFetchError"
Cohesion: 0.22
Nodes (9): PriceFetchError, RuntimeError, Gagal mengambil harga nyata dari penyedia.      Dilempar alih-alih mengembalikan, Kegagalan jaringan tidak boleh diam-diam jadi data sintetis., Satu aset gagal tidak menghentikan yang lain; error dicatat., test_fetch_failure_raises_instead_of_returning_synthetic(), test_fetch_universe_continues_when_one_asset_fails(), test_parse_yahoo_raises_on_empty_result() (+1 more)

### Community 96 - "FinbertGoldSentiment"
Cohesion: 0.15
Nodes (8): FinbertGoldSentiment, ndarray, Path, Versi dari metrics.json bila ada, agar dapat diaudit per-artefak., Kembalikan probabilitas terkalibrasi, urutan `[pos, neu, neg]`., Logits mentah (untuk temperature scaling saat kalibrasi).          Urutan kolom, Skor satu artikel → ArticleSentiment terkalibrasi.          Ambang ±0.10 sama de, FinBERT yang di-fine-tune pada korpus berita emas Sinha.

### Community 97 - "sim_input.py"
Cohesion: 0.12
Nodes (18): BaseModel, Badan permintaan /api/simulate.      `kind` sengaja tanpa nilai bawaan. Kalau pu, SimulateRequest, _has_phrase(), _has_reporting_cue(), _has_rumor_cues(), InputKind, _is_small_talk() (+10 more)

### Community 98 - "evaluate_holdout.py"
Cohesion: 0.11
Nodes (19): Validates McNemar 2x2 contingency table calculation and p-value., Validates bootstrap 95% confidence interval for difference in Macro F1., test_compute_bootstrap_ci(), test_compute_mcnemar_significance(), Seed yang sama harus menghasilkan angka identik., Bila roberta jauh lebih baik, batas bawah CI harus > 0., Dua model identik -> selisih 0, CI memuat 0 (tidak signifikan)., Sanity check: seed benar-benar dipakai, bukan diabaikan. (+11 more)

### Community 101 - "test_fomc_track.py"
Cohesion: 0.11
Nodes (28): Unit tests for FOMC track data loader and methodology contracts., Validates training and serializing the FOMC baseline TF-IDF + LR model., Validates BaseSentimentModel protocol compliance without downloading heavy check, Validates that train set loads exactly 1.939 valid rows with required columns., Validates stratified 90:10 split (1.745 train vs 194 validation)., Validates that official unseen test set has exactly 495 rows., Validates monetary stance transmission invariant to RATE_UST and SPX., Validates extracting clean lists of texts and integer labels. (+20 more)

### Community 102 - "TestLabelContract"
Cohesion: 0.18
Nodes (7): Mapping label harus cocok dengan protokol dan adapters backend., README model/xau menetapkan Positive→2, Neutral→1, Negative→0., Loader model dan jalur ingest harus memetakan tone dengan cara sama.          Ka, Baris `none` harus hilang, bukan berubah jadi neutral., TestLabelContract, normalize_tone(), Petakan nilai `Price Sentiment` mentah ke tone baku, atau None.      None berart

### Community 103 - "test_xau_track.py"
Cohesion: 0.14
Nodes (19): Test track FinBERT-EMAS (FR-6 / M2 + M6).  Fokus pada hal yang **tidak butuh PyT, Duplikat antar-split akan membocorkan contoh test ke train., Kebersihan data nyata pada parquet lokal., TestSanitize, get_texts_and_labels(), load_gold_test(), load_gold_test_holdout(), load_gold_train() (+11 more)

### Community 104 - "IngestScheduler"
Cohesion: 0.15
Nodes (11): default_db_path(), IngestScheduler, datetime, Path, Penjadwal preload berita harian pukul 07:00 WIB.  Kenapa modul ini ada ---------, Nyalakan thread latar. Idempoten: panggilan kedua diabaikan., Satu langkah pemeriksaan, dipisah agar bisa diuji tanpa thread., Jalankan bila slot sudah tiba dan belum ada run sukses untuk slot itu. (+3 more)

### Community 105 - "test_yfinance_collector.py"
Cohesion: 0.17
Nodes (12): Uji `PriceCollector` (backend/src/collect/yfinance_collector.py).  Modul ini seb, Hari libur / bar tidak lengkap harus dilewati, bukan jadi 0., Bila open/high/low None, pakai close -- jangan hasilkan None., Timestamp ada tapi semua close null -> tidak boleh mengembalikan []., Payload hasil json.loads (bukan dict langsung) juga harus terbaca., test_parse_yahoo_falls_back_to_close_for_missing_ohlc(), test_parse_yahoo_json_roundtrip(), test_parse_yahoo_produces_records_with_utc_dates() (+4 more)

### Community 106 - "ParquetStore"
Cohesion: 0.20
Nodes (8): ParquetStore, Any, DataFrame, Path, Parquet storage helpers for bulk dumps and training datasets., Manages Parquet writes and reads for processed time series., Saves records to a Parquet file., Reads records from a Parquet file.

### Community 107 - "TemperatureScaler"
Cohesion: 0.24
Nodes (7): Validates TemperatureScaler fitting, scaling, and JSON persistence., test_temperature_scaler_fit_and_persistence(), Path, Saves temperature calibration metadata to JSON file., Loads temperature parameter from JSON file., Scales logits by optimal temperature parameter T to calibrate prediction probabi, TemperatureScaler

### Community 108 - "TestPrioritasModel"
Cohesion: 0.17
Nodes (6): P0-3: prioritas model adalah data eksplisit, bukan urutan `if`., Tiap baris harus punya loader & `score_space` yang sah., FOMC mengukur stance; kalau ditandai `price`, P0-2 kembali bug., FinBERT-EMAS dilatih pada sentimen harga emas, bukan stance Fed., Nama loader harus benar-benar ada, bukan string mati., TestPrioritasModel

### Community 109 - "evaluate.py"
Cohesion: 0.31
Nodes (9): build_report(), evaluate(), main(), _print_summary(), Any, Path, Evaluasi artefak FinBERT-EMAS pada holdout test (M6).  Jalankan setelah training, Rakit laporan evaluasi dari prediksi & probabilitas yang sudah dihitung.      Di (+1 more)

### Community 110 - "train_xau_finbert.py"
Cohesion: 0.21
Nodes (12): Neutral hanya ~4%; stratifikasi menjamin ia hadir di validation., Pisahkan validation dari train untuk early stopping + temperature.      Stratifi, split_train_val(), _class_report(), _macro_f1(), main(), Any, ndarray (+4 more)

### Community 111 - "PriceCollector"
Cohesion: 0.18
Nodes (9): Market data and news collectors., PriceCollector, Path, Fetches daily prices for core locked universe assets., collector(), Kolektor dengan peta ticker buatan sendiri (tidak menyentuh data repo)., Tanpa file master, kolektor tetap dibuat; fetch yang akan menolak., test_fetch_universe_raises_only_when_all_fail() (+1 more)

### Community 112 - "softmax"
Cohesion: 0.22
Nodes (8): Validates invariant that probabilities always sum to 1.0 and soften with higher, test_softmax_temperature_properties(), ndarray, Finds optimal temperature T by minimizing Negative Log-Likelihood (NLL) on valid, Scales raw logits by learned temperature: z / T., Converts raw logits to calibrated probabilities summing to 1.0., Computes numerically stable softmax probabilities with temperature scaling., softmax()

### Community 113 - "train_fomc_roberta.py"
Cohesion: 0.29
Nodes (10): _class_report(), _macro_f1(), main(), Any, ndarray, Path, Latih FOMC-RoBERTa pada korpus FOMC (P0-1).  Resep mengikuti rilis upstream yang, Presisi/recall/F1 per kelas — tanpa ini, rata-rata menyembunyikan neutral. (+2 more)

### Community 114 - "overview.js"
Cohesion: 0.26
Nodes (14): bindPager(), ensureChart(), hitungCakupan(), isoDaysAgo(), loadPreloadStamp(), newsItem(), renderAll(), renderChart() (+6 more)

### Community 115 - "🏛️ ARCAS — Monetary Policy Track (FOMC)"
Cohesion: 0.18
Nodes (11): 1. Hasil Benchmark Resmi (Holdout 495 Sampel Beku), 2. Preprocessing Khusus Domain Finansial FOMC, 3. Arsitektur Pipeline End-to-End ARCAS, 4. Mekanisme Fail-Safe: Dual-Checkpoint Auto-Fallback, 4a. Status Artefak: Apa yang Benar-Benar Bisa Dipakai Hari Ini, 5. Struktur Direktori Track FOMC, 7. Sitasi Akademik, 🏛️ ARCAS — Monetary Policy Track (FOMC) (+3 more)

### Community 116 - "TestProbabilityOrder"
Cohesion: 0.25
Nodes (5): Path, Urutan probabilitas harus [pos, neu, neg] sesuai protokol., Simulasi: logits condong ke kelas 2 (positive) harus jadi p_pos tertinggi., Tanpa artefak, error harus menuntun ke skrip latih, bukan segfault., TestProbabilityOrder

### Community 117 - "research.js"
Cohesion: 0.29
Nodes (12): barisBuktiKeputusan(), drawPriceChart(), jejakHarga(), judulBerita(), loadData(), nearestTradingDate(), perbaruiPetunjuk(), persenBertanda() (+4 more)

### Community 118 - "PriceRecord"
Cohesion: 0.28
Nodes (7): FetchResult, Price data collector for the 3 core locked assets (XAU, RATE_UST, SPX).  Sumber, Hasil satu penarikan harga, termasuk asal datanya., PriceRecord, Tests price storage and retrieval., test_db_price_crud(), test_fetch_with_meta_marks_source_as_yahoo()

### Community 119 - "StatEngine"
Cohesion: 0.18
Nodes (11): StatResult, DataFrame, date, Deterministic statistical engine for sentiment-market association., Frame bersih: terurut tanggal, kolom `return`, tanpa baris kosong.          Sent, Aturan bandwidth Newey-West: floor(4 * (n/100) ** (2/9))., Uji kausalitas Granger: apakah sentimen membantu memprediksi return.          Ar, Executes deterministic econometric tests between sentiment and market metrics. (+3 more)

### Community 120 - "train_fomc_baseline"
Cohesion: 0.50
Nodes (4): LogisticRegression, DataFrame, Trains Baseline TF-IDF + Logistic Regression on FOMC train set.      Label mappi, train_fomc_baseline()

### Community 121 - "1. Aturan Domain"
Cohesion: 0.33
Nodes (6): 1.1 Definisi, 1.2 `basis` dan batas confidence, 1.3 Evidence & rationale, 1.4 Target, 1.5 Disclaimer, 1. Aturan Domain

### Community 122 - "simulations.js"
Cohesion: 0.19
Nodes (21): barisBukti(), gambarGrafik(), giliran(), isiBacktest(), isiKartuKeputusan(), isiKeputusan(), kartuBacktest(), kartuBawah() (+13 more)

### Community 123 - "SimulationService"
Cohesion: 0.15
Nodes (9): _nama_persona(), Path, Pemegang model. Dimuat sekali, dipakai berkali-kali., True/False bila sudah dicoba dimuat, None bila belum., Pilih model untuk SATU teks lewat ModelRouter, lalu muat.          Memilih satu, Evaluasi lima persona memakai engine yang sudah ada., Nama tampilan persona dari berkas konfigurasi, bukan hardcode di GUI., SimulationService (+1 more)

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

### Community 129 - "evidence.js"
Cohesion: 0.20
Nodes (16): applyNewsFilter(), bindPager(), bindPersonaButtons(), evidenceDrawer(), impactCard(), potongHalaman(), renderAll(), renderHalaman() (+8 more)

### Community 130 - "4. Tujuan & Non-Tujuan"
Cohesion: 0.67
Nodes (3): 4. Tujuan & Non-Tujuan, Goals, Non-Goals (v1)

### Community 131 - "api.js"
Cohesion: 0.60
Nodes (3): api(), detectBase(), resetBase()

### Community 135 - "test_stat_unique.py"
Cohesion: 0.22
Nodes (16): db(), _jumlah(), `stat_results` tidak boleh punya dua baris yang menyatakan bukti yang sama.  Lat, DB produksi sudah berisi 12 baris kembar; migrasi harus membersihkannya., init_schema dipanggil setiap start; menjalankannya dua kali harus aman., Bukan hanya lewat save_stats: tabel sendiri yang menolak., `event_study` ber-lag NULL; UNIQUE biasa akan meloloskannya., Lag berbeda adalah uji berbeda; kunci unik tidak boleh menelannya. (+8 more)

### Community 137 - "test_ingest_orphan_runs.py"
Cohesion: 0.31
Nodes (15): _baris(), _db(), datetime, Path, Run ingest yatim harus ditutup saat startup.  Proses yang mati antara `claim_ing, Proses yang benar-benar masih berjalan tidak boleh dicap gagal., Run yatim punya finished_at paling baru; ia tidak boleh jadi cap waktu.      Kal, _sisip() (+7 more)

### Community 138 - "test_sim_state.py"
Cohesion: 0.17
Nodes (13): _ModelPalsu, Uji P2-8 dan P2-9 tanpa memuat bobot model.  Keduanya cacat pada `SimulationServ, Kebalikannya: netral yang wajar tidak boleh diberi peringatan palsu., Model cukup untuk melewati jalur skoring tanpa bobot sungguhan., Service dengan model palsu di cache untuk SEMUA entri PRIORITAS.      Nama kunci, Setelah analyze, tidak boleh ada sisa nilai yang bisa dibaca request lain., Bukti langsung: analyze paralel harus mengembalikan hasil yang konsisten.      T, Kegagalan routing harus terlihat di `warnings`, bukan diam-diam netral. (+5 more)

### Community 139 - ".compute_car_event_study"
Cohesion: 0.29
Nodes (13): Event study: Cumulative Abnormal Returns (CAR) around sentiment spikes., _closes_with_one_spike(), _frame(), CAR event study: tersambung ke CLI, jendela memakai posisi, CI tidak dikarang., Return harian nol kecuali satu hari, supaya CAR bisa dihitung tangan., Satu baris close NaN di depan tidak boleh menggeser jendela event.      Dulu fun, n=1 tidak punya sebaran: CI harus None, bukan angka karangan., test_car_multiple_events_produce_ci_around_estimate() (+5 more)

### Community 140 - "compute_multiclass_ece"
Cohesion: 0.17
Nodes (10): Validates multi-class Expected Calibration Error (ECE) metric., test_multiclass_ece_calculation(), Test untuk perhitungan laporan evaluasi XAU (audit P1-5).  Audit mencatat `model, ECE multiclass yang dipakai laporan XAU harus menangani confidence 1.0.      Fun, Regresi: confidence tepat 1.0 harus masuk bin terakhir.          Bila batas bin, Probabilitas seragam = akurasi ~1/3 = confidence ~1/3 -> ECE kecil., TestECEUntukLaporanXAU, compute_multiclass_ece() (+2 more)

### Community 141 - "TestBuildReport"
Cohesion: 0.19
Nodes (6): Baris = label sebenarnya, kolom = prediksi. Sampel ke-4 (true 0 -> 1)., Target 0.1 harus dinilai dari `ece_post`, bukan `ece_pre`.          Kasus pentin, Holdout bisa saja tidak memuat satu kelas; laporan tidak boleh crash., Laporan harus JSON-serializable: `evaluate` menulisnya ke disk., 3 dari 4 benar -> akurasi 0.75., TestBuildReport

### Community 142 - "verify_local"
Cohesion: 0.23
Nodes (12): `--verify-only` harus lulus pada bobot yang sehat.          Dilewati bila bobot, download_hf(), main(), print_checksums(), Any, Path, Hitung SHA256 tanpa memuat seluruh berkas (bobot bisa >1 GB)., Verifikasi bobot yang sudah ada di disk. Kembalikan daftar masalah. (+4 more)

### Community 143 - "test_stats_engine.py"
Cohesion: 0.22
Nodes (11): Any, Assembles the engine input frame from daily sentiment and price records., _demo_daily_prices(), StatEngine multi-lag tests for the association workbench (Upgrade.md UI-05)., Deterministic series: news on even days, alternating score and close., Merged frame keeps engine columns; news-free days stay NaN, not 0., Live computation returns one result per lag 0..max_lag, metric=return., test_frame_from_empty_inputs_is_empty() (+3 more)

### Community 144 - "TestDegradasiModelTerlihat"
Cohesion: 0.23
Nodes (8): _artikel(), pipeline(), Jalur sukses tidak boleh menghasilkan peringatan palsu.          Peringatan yang, Kegagalan memuat RoBERTa harus muncul di ringkasan, bukan cuma log., `score_and_route` harus meneruskan degradasi ke PipelineStats.errors.          I, `ringkas()` (dipakai CLI) wajib menyebut jumlah error.          Degradasi yang t, Ketiadaan torch juga harus eksplisit, bukan fallback senyap., TestDegradasiModelTerlihat

### Community 145 - "test_persistence.py"
Cohesion: 0.15
Nodes (9): Tests for S-2: persona_views & alloc_suggestions harus dipersistensi.  NFR repro, Audit butuh jejak: versi parameter dan waktu pembuatan., Yang disimpan harus sama dengan yang dikirim ke klien., Pemanggilan ulang harus menimpa, bukan menumpuk baris kembar., Tidak ada dampak -> tidak ada yang disimpan (jangan simpan karangan)., test_persisted_persona_matches_response(), test_persisted_rows_carry_provenance(), test_persona_not_stored_when_endpoint_404() (+1 more)

### Community 146 - "test_research_trace_js.py"
Cohesion: 0.23
Nodes (12): _jalankan(), _jejak(), Jejak harga T+n harus membedakan dua sebab kosong yang berbeda artinya.  - "sesi, Muat research.js di ctx minimal: cukup A.esc + A.state, tanpa DOM., idx=2: T+1 pun sudah di luar deret, karena harga berhenti di 11-05., idx=-1: tanggal berita tidak ada di deret sama sekali -> cacat data., Sesi belum terjadi bukan cacat data; cacat data bukan sesi., test_berita_di_luar_deret_harga_disebut_tanggal_tidak_di_deret() (+4 more)

### Community 147 - "test_sim_readiness.py"
Cohesion: 0.18
Nodes (12): _client(), Uji kesiapan model (P1-9) tanpa memuat bobot 440 MB.  Sebelum P1-9, request pert, None berarti warm-up belum dicoba -- bukan berarti gagal., Warm-up yang gagal harus melaporkan alasan, bukan meledak., Bila minimal satu model termuat, status harus True., None = warm-up belum dicoba -> jalur lambat harus tetap jalan.      Tanpa ini, d, svc(), test_endpoint_503_saat_model_gagal_dimuat() (+4 more)

### Community 148 - "daily_headline.py"
Cohesion: 0.26
Nodes (11): main(), _muat_cache(), date, datetime, Path, Tarik 1 headline/hari (XAU / RATE_UST / SPX) untuk 6 bulan terakhir via Finnhub., Tarik semua berita untuk daftar simbol pada rentang tanggal., Skor tiap berita untuk target, urut skor desc lalu waktu desc. (+3 more)

### Community 149 - "news_preload.py"
Cohesion: 0.27
Nodes (11): _collect_via_eulerpool(), datetime, Path, Job preload berita: satu tarikan terjadwal -> rantai penuh sampai `impacts`.  Ra, Jalankan clean -> score -> aggregate lewat Pipeline yang sudah ada., Satu siklus preload untuk `slot`. True bila setidaknya penarikan berhasil., Tarik berita eulerpool dan simpan ke raw_articles.      Mengembalikan (jumlah_ba, Tarik harga harian terbaru dan simpan ke tabel `prices`.      Kenapa di sini: `P (+3 more)

### Community 150 - "test_evidence_pager_js.py"
Cohesion: 0.36
Nodes (11): _baris(), _jalankan(), Pager halaman bukti: 10 kartu per halaman, saringan atas SELURUH baris.  Halaman, Arah bearish tersebar di 50 baris; saringan harus menemukan semuanya., test_data_lima_belas_jadi_dua_halaman_lima_ekor(), test_halaman_di_luar_rentang_dipangkas_ke_terakhir(), test_halaman_terakhir_berisi_sisanya(), test_saringan_arah_melihat_seluruh_populasi_bukan_satu_halaman() (+3 more)

### Community 151 - "softmax_with_temperature"
Cohesion: 0.23
Nodes (7): T > 1 melembutkan; T < 1 menajamkan. Ini inti kalibrasi suhu., Suhu 0 (artefak kalibrasi rusak) tidak boleh menghasilkan NaN., Kalibrasi suhu tidak boleh mengubah kelas prediksi.          Bila berubah, lapor, TestSoftmaxDenganSuhu, ndarray, Softmax dengan suhu `t`. `t=1.0` = softmax biasa.      Diangkat dari dalam `eval, softmax_with_temperature()

### Community 152 - "test_fade_guard_js.py"
Cohesion: 0.27
Nodes (9): _fade_lalu(), Fade halaman tidak boleh dipotong animationend milik elemen anak.  `.panel` dan, Tanpa parameter, event tidak bisa diperiksa asalnya., Tanpa reflow, browser bisa menggabungkan dua state dan animasi tak jalan., test_fade_out_dilepas_sebelum_fade_in_dipasang(), test_handler_menerima_argumen_event(), test_handler_menolak_event_dari_anak(), test_reduced_motion_melewati_fade_sepenuhnya() (+1 more)

### Community 153 - "compute_ece"
Cohesion: 0.25
Nodes (6): `compute_ece` (single-label, deprecated) -- lihat catatan modul.      Kontrak se, Model yakin 1.0 tetapi semua salah -> ECE mendekati 1.0.          Regresi yang d, Mendokumentasikan keanehan: `probs` tidak memengaruhi hasil., TestECE, compute_ece(), Computes Expected Calibration Error (ECE) untuk kasus single-label.      Catatan

### Community 154 - "test_stat_replace.py"
Cohesion: 0.25
Nodes (10): db(), stat_results harus diganti, bukan ditumpuk, setiap pipeline dijalankan ulang.  K, Batch kedua menggantikan batch pertama, bukan menumpuk di sampingnya., Bukan hanya jumlahnya sama — nilainya harus dari run terakhir., Menghapus per aset, supaya aset yang gagal dihitung tetap punya hasil., _stat(), test_aset_lain_tidak_ikut_terhapus(), test_hasil_baru_benar_benar_menggantikan_yang_lama() (+2 more)

### Community 155 - "backfill_news.py"
Cohesion: 0.36
Nodes (10): backfill(), _bulan(), main(), _muat_state(), datetime, Path, Backfill berita historis 1 tahun dari Marketaux ke raw_articles.  Kenapa modul t, Potong rentang jadi jendela ~30 hari, dibatasi `sampai`. (+2 more)

### Community 156 - "TestMcNemar"
Cohesion: 0.20
Nodes (6): Uji McNemar dengan koreksi kontinuitas Edwards., Angka chi2 dan p dihitung manual dari tabel kontingensi.          Skenario 10 sa, `component_adopted` mensyaratkan p<0.05 DAN n01>n10.          Signifikansi saja, Bila kedua model identik, tabel diskordan nol -> p=1.0., Keempat sel harus berjumlah sama dengan jumlah sampel., TestMcNemar

### Community 157 - "test_overview_hero_json.py"
Cohesion: 0.29
Nodes (9): _cakupan(), Kartu ketiga di hero ikhtisar: cakupan berita pada rentang yang dipilih.  Kartu, score_mean null tidak dihitung sebagai hari berita., 5 hari bursa, 2 punya berita -> 2 dari 5 (40%)., Pembagi tidak diketahui -> persen null, bukan 0% yang menyesatkan., test_cakupan_memakai_jumlah_hari_bursa_bila_diberi(), test_hari_berita_dihitung_dari_yang_punya_artikel(), test_hari_tanpa_artikel_bukan_hari_berita() (+1 more)

### Community 158 - "test_sim_chart_lifecycle.py"
Cohesion: 0.29
Nodes (9): Grafik simulasi tidak boleh menumpuk listener resize.  Empat giliran dulu menamb, Satu listener global, bukan satu per grafik.      Bentuk lama: `addEventListener, simUlang harus dispose, bukan hanya mengosongkan innerHTML., Tanpa delete, kunci mati tetap ada dan ikut di-resize selamanya., _src(), test_dispose_menghapus_kunci_dari_peta(), test_listener_resize_dipasang_sekali_di_luar_gambar_grafik(), test_listener_resize_mengiterasi_semua_grafik() (+1 more)

### Community 159 - "test_metrics.py"
Cohesion: 0.28
Nodes (6): Test untuk metrik evaluasi bersama (`model/common/metrics.py`).  Audit P1-5 menc, TestEvaluatePredictions, Tests F1 macro, accuracy, and kappa computation., test_evaluation_metrics(), evaluate_predictions(), Calculates macro-F1, accuracy, and cohen kappa.

### Community 160 - "test_sim_card_ids.py"
Cohesion: 0.36
Nodes (8): _kartu(), Tiap kartu simulasi punya id stabil dan data-target.  Dua kartu dirender per gil, Id section dan id body tidak boleh sama., test_data_target_mengikuti_target_giliran(), test_id_body_keputusan_tidak_bentrok_dengan_section(), test_section_punya_id_stabil(), test_section_punya_satu_data_target(), test_semua_id_dalam_satu_kartu_unik()

### Community 161 - "Evaluasi Model ARCAS"
Cohesion: 0.22
Nodes (8): Emas (FinBERT-EMAS), Evaluasi Model ARCAS, FOMC (RoBERTa), Matriks konfusi, Per kelas, Ringkasan pada set uji, Router: pemilihan model spesialis, Yang belum dievaluasi

### Community 162 - "sim-decision.js"
Cohesion: 0.36
Nodes (7): agregasiStance(), ambangDariWarnings(), keputusanBerita(), keputusanDariBukti(), persen(), rapikanKeHariBursa(), selisihHari()

### Community 163 - "conftest.py"
Cohesion: 0.29
Nodes (6): Path, Fixture bersama untuk seluruh suite `backend/tests`.  Sebelumnya `temp_db` didef, Database SQLite sementara dengan skema lengkap.      Nama berkas memakai `tmp_pa, Jangan pernah menyalakan scheduler atau memuat bobot 440 MB saat tes.      Sebel, _tanpa_scheduler_dan_warmup(), temp_db()

### Community 164 - ".benjamini_hochberg"
Cohesion: 0.40
Nodes (4): Calculates adjusted p-values using the Benjamini-Hochberg FDR procedure., Implementasi sendiri harus identik dengan referensi statsmodels., test_benjamini_hochberg_handles_empty(), test_benjamini_hochberg_matches_statsmodels_reference()

### Community 165 - ".hitung_hari_berpasangan"
Cohesion: 0.50
Nodes (3): Jumlah tanggal yang punya sentimen DAN harga sekaligus.          Dipakai untuk m, Hanya tanggal yang punya sentimen DAN harga yang dihitung., test_hitung_hari_berpasangan_hanya_tanggal_irisan()

## Knowledge Gaps
- **294 isolated node(s):** `finews`, `graph.sh script`, `GRAPHIFY_OUT`, `1. Mulai dari sini, bukan dari `ls -R``, `2. Peta cepat: di mana apa` (+289 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **35 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `Database` to `cli.py`, `seeded_db`, `test_manual_ingest.py`, `.get_impact_for_article`, `.query_articles_by_target`, `test_stat_unique.py`, `news_cli.py`, `.save_price`, `Lang`, `test_dedup.py`, `main`, `test_ingest_orphan_runs.py`, `.get_connection`, `test_persistence.py`, `schema.py`, `news_preload.py`, `daily_headline.py`, `test_pipeline_integration.py`, `Pipeline`, `test_stat_replace.py`, `backfill_news.py`, `test_db.py`, `test_news_cli.py`, `test_source_health.py`, `conftest.py`, `app.py`, `validate`, `.hash_text`, `.claim_ingest_slot`, `.finish_ingest_run`, `.get_alloc_suggestions`, `.get_persona_views`, `.has_run_for_slot`, `DailySentiment`, `.is_valid_target`, `.last_ingest_run`, `date`, `.latest_source_health`, `.query_impact_time_audit`, `.save_articles`, `.save_sentiment`, `test_sim_api.py`, `.seed_aliases`, `Connection`, `.save_label`, `.get_active_universe`, `test_effective_trading_date.py`, `Article`, `.save_persona_views`, `test_schema_version.py`, `test_news_preload.py`, `ArticleSentiment`, `sim_input.py`, `.save_article`, `.save_daily_sentiment`, `PriceRecord`, `StatEngine`?**
  _High betweenness centrality (0.225) - this node is a cross-community bridge._
- **Why does `Pipeline` connect `Pipeline` to `cli.py`, `Database`, `BaselineTfidfSentiment`, `test_effective_trading_date.py`, `Lang`, `test_dedup.py`, `DailySentiment`, `ModelRouter`, `Article`, `TargetRouter`, `TestDegradasiModelTerlihat`, `TestPrioritasModel`, `schema.py`, `news_preload.py`, `test_pipeline_integration.py`, `ArticleSentiment`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Why does `FOMCRoBERTaSentiment` connect `Article` to `evaluate_holdout.py`, `test_fomc_track.py`, `Lang`, `TemperatureScaler`, `test_fomc_cache_recovery.py`, `model.py`, `Pipeline`, `SimulationService`, `ArticleSentiment`?**
  _High betweenness centrality (0.065) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Database` (e.g. with `Pipeline` and `PipelineError`) actually correct?**
  _`Database` has 16 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Pipeline` (e.g. with `DailyAggregator` and `ArticleCleaner`) actually correct?**
  _`Pipeline` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 18 inferred relationships involving `TargetRouter` (e.g. with `Pipeline` and `PipelineError`) actually correct?**
  _`TargetRouter` has 18 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Article` (e.g. with `ArticleCleaner` and `NearDuplicateDetector`) actually correct?**
  _`Article` has 17 INFERRED edges - model-reasoned connections that need verification._