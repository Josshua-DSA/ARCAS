# Graph Report - FInews  (2026-10-21)

## Corpus Check
- 75 files · ~78,921 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 715 nodes · 1093 edges · 52 communities (39 shown, 13 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 37 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `fc47e72e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- schema.py
- DESIGN — Model, Scoring, Statistik & Antarmuka
- app.js
- BaselineTfidfSentiment
- adapters.py
- Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro
- ModelRouter
- StatEngine
- DailySentiment
- Dataset Card for Sentiment Analysis of Commodity News (Gold)
- TargetImpact
- PRD — Financial News Sentiment & Market Association System
- RULES — Aturan Wajib Proyek
- Upgrade UI FInews
- PriceRecord
- GUI THEME — Claude × Bloomberg
- .get_connection
- ARCHITECTURE — Financial News Sentiment & Market Association System
- ReportExporter
- Database
- FinNews: Financial News Sentiment & Market Association System
- ParquetStore
- SCHEMA — Data Contracts
- Model Router: Cascade Routing ke Model Spesialis
- .query_daily_sentiment
- .init_schema
- .route_article
- fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX)
- xau/ — Track FinBERT-EMAS (target XAU)
- StatResult
- dataset/ — Katalog Data
- Theme & Splash — Bloomberg 70% × Claude 30%
- Model Research Notebooks
- model/ — ML Research & Inference Pipeline (M1–M7)
- research/ — Ringkasan Paper Terkait
- frontend/GUI/ — Static ECharts HTML Dashboard (FR-15)
- README.md
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
1. `Database` - 39 edges
2. `TargetImpact` - 18 edges
3. `ModelRouter` - 18 edges
4. `DailySentiment` - 17 edges
5. `TargetRouter` - 16 edges
6. `BaselineTfidfSentiment` - 16 edges
7. `AllocationEngine` - 15 edges
8. `PersonaEngine` - 15 edges
9. `PriceRecord` - 15 edges
10. `PRD — Financial News Sentiment & Market Association System` - 15 edges

## Surprising Connections (you probably didn't know these)
- `BaselineTfidfSentiment` --uses--> `Tone`  [INFERRED]
  model/common/baseline.py → backend/src/schema.py
- `BaselineTfidfSentiment` --uses--> `ModelProbs`  [INFERRED]
  model/common/baseline.py → backend/src/schema.py
- `BaselineTfidfSentiment` --uses--> `ArticleSentiment`  [INFERRED]
  model/common/baseline.py → backend/src/schema.py
- `BaseSentimentModel` --uses--> `ModelProbs`  [INFERRED]
  model/common/protocol.py → backend/src/schema.py
- `BaseSentimentModel` --uses--> `ArticleSentiment`  [INFERRED]
  model/common/protocol.py → backend/src/schema.py

## Import Cycles
- None detected.

## Communities (52 total, 13 thin omitted)

### Community 0 - "schema.py"
Cohesion: 0.10
Nodes (22): PersonaEngine, Path, Deterministic Persona POV engine computing BUY/HOLD/SELL stances., Evaluates 5 investor personas stances for a given impact., Calculates decay/alignment between news horizon and persona horizon., Calculates stance for a specific persona based on parameters.         Determinis, Evaluates all 5 personas., Persona POV simulation engine. (+14 more)

### Community 1 - "DESIGN — Model, Scoring, Statistik & Antarmuka"
Cohesion: 0.04
Nodes (47): 10. Keterbatasan, 11.1 Kelas aset, 11.2 Skor per kelas (`alloc_map.yaml`), 11.3 Rumus, 11.4 Preset profil (contoh, bisa diubah; total wajib 100%), 11.5 Output, 11. Allocation Tilt, 12.1 Persona awal (`personas.yaml`) (+39 more)

### Community 2 - "app.js"
Cohesion: 0.11
Nodes (46): api(), applyNewsFilter(), bindControls(), bindPersonaButtons(), bindTabs(), demoImpacts(), demoQuality(), demoSeries() (+38 more)

### Community 3 - "BaselineTfidfSentiment"
Cohesion: 0.10
Nodes (18): Tests for baseline ML model and evaluation metrics., Tests F1 macro, accuracy, and kappa computation., Tests TF-IDF + LR baseline model predictions., test_baseline_tfidf_predict(), test_evaluation_metrics(), 01_baseline_exploration.py  Eksplorasi baseline model (M1: TF-IDF + Logistic Reg, Menjalankan pelatihan dan evaluasi baseline sentiment.     Labels: 0 = Negative,, run_experiment() (+10 more)

### Community 4 - "adapters.py"
Cohesion: 0.11
Nodes (29): fomc_stance(), fomc_to_raw(), fomc_tone(), _gold_parse_date(), gold_to_raw(), gold_tone(), DataFrame, datetime (+21 more)

### Community 5 - "Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro"
Cohesion: 0.06
Nodes (31): 1.1 Masalah & Problem Statement, 1.2 Objektif, Metrik Domain, dan Metrik Teknis, 1.3 Uji Kecocokan Solusi (Component Necessity Test), 1. Problem Framing, 2.1 Tujuan Sistem, 2.2 Prinsip Desain, 2.3 Cakupan 3 Target Makro Terkunci (Murni 3 v2026-10-11-p3), 2. Deskripsi Sistem (+23 more)

### Community 6 - "ModelRouter"
Cohesion: 0.10
Nodes (24): ModelRouter, Path, Two-stage cascade router: news text -> specialist model id.  Tahap 1: petunjuk s, Lowercase token tanpa stopword. Dipakai builder dan router., Routes an article to the specialist model that should score it., Rata-rata z dan jumlah bukti kuat per domain., Returns (model_ids, reason, score). reason: source|keyword|log_odds|fallback., tokens() (+16 more)

### Community 7 - "StatEngine"
Cohesion: 0.12
Nodes (21): StatResult, Any, DataFrame, date, Deterministic statistical engine for sentiment-market association., Event study: Cumulative Abnormal Returns (CAR) around sentiment spikes., Executes deterministic econometric tests between sentiment and market metrics., Assembles the engine input frame from daily sentiment and price records. (+13 more)

### Community 8 - "DailySentiment"
Cohesion: 0.16
Nodes (13): DailyAggregator, date, Aggregates article impacts into daily sentiment series., Computes daily mean and weighted sentiment per target., Aggregates impacts for a single asset on a given trading date.         Strict in, Aggregates batch of impacts, explicitly creating empty records         with scor, Daily sentiment aggregation across assets., DailySentiment (+5 more)

### Community 9 - "Dataset Card for Sentiment Analysis of Commodity News (Gold)"
Cohesion: 0.09
Nodes (22): Acknowledgements, Bias, Risks, and Limitations, Citation, Content, Context, Curation Rationale, Data Collection and Processing, Data Fields (+14 more)

### Community 10 - "TargetImpact"
Cohesion: 0.05
Nodes (52): ABC, AllocationEngine, Path, Deterministic Allocation Tilt engine satisfying strict 100% sum constraint., Computes relative portfolio tilt adjustments from asset scores., Derives scores for 6 allocation classes using alloc_map.yaml.         Score tupl, Calculates constrained allocation tilt for a specific profile.         Strictly, Allocation Tilt simulation engine. (+44 more)

### Community 11 - "PRD — Financial News Sentiment & Market Association System"
Cohesion: 0.10
Nodes (20): 10. Sumber Data (ringkas; detail di `ARCHITECTURE.md` §4), 11. Fase, 12. Risiko, 13. Open Questions, 14.1 Allocation Tilt, 14.2 Persona POV (5 persona), 14.3 Catatan Penting, 14. Fitur Tambahan (v0.3) (+12 more)

### Community 12 - "RULES — Aturan Wajib Proyek"
Cohesion: 0.10
Nodes (20): 10. Untuk AI Assistant yang Mengerjakan Repo Ini, 11.1 Aturan Frontend (GUI Web & TUI), 11. Aturan Allocation Tilt & Persona POV (v0.3), 1.1 Definisi, 1.2 `basis` dan batas confidence, 1.3 Evidence & rationale, 1.4 Target, 1.5 Disclaimer (+12 more)

### Community 13 - "Upgrade UI FInews"
Cohesion: 0.10
Nodes (20): 1. Tujuan, 2. Kondisi UI Saat Ini, 3.1 Adaptasi Splash Screen yang Sudah Ada, 3. Struktur Halaman yang Direkomendasikan, 4. Prioritas Upgrade, 5. Perubahan Kontrak Minimum, 6. Urutan Implementasi, 7. Yang Sengaja Tidak Dibuat (+12 more)

### Community 14 - "PriceRecord"
Cohesion: 0.17
Nodes (9): Market data and news collectors., PriceCollector, date, Path, Price data collector for the 3 core locked assets (XAU, RATE_UST, SPX)., Fetches daily prices for core locked universe assets., Fetches prices for all active core assets (XAU, RATE_UST, SPX)., Generates realistic synthetic daily price series for testing or offline simulati (+1 more)

### Community 15 - "GUI THEME — Claude × Bloomberg"
Cohesion: 0.12
Nodes (15): 10. Tipografi (ringkas; versi font gratis padanan), 11. CSS Variables (siap salin), 12. Konfigurasi Streamlit (jika dipakai; cek dukungan font kustom pada versi yang dipakai), 13. Daftar Periksa Implementasi, 1. Konsep, 2. Warna Inti (dari spesifikasi), 3. Token Turunan — Sisi Terang, 4. Token Turunan — Sisi Gelap (Technical Surface) (+7 more)

### Community 16 - ".get_connection"
Cohesion: 0.12
Nodes (14): Database, Manages SQLite connections and queries for FInews., Stores a TargetImpact record., Stores daily aggregate sentiment for an asset., Stores a daily asset price., Returns all 3 active core universe assets., Returns real provenance facts for GET /api/meta.          Everything comes from, Checks if a target belongs to the 3 core locked universe. (+6 more)

### Community 17 - "ARCHITECTURE — Financial News Sentiment & Market Association System"
Cohesion: 0.14
Nodes (13): 10. Kontrak Penyajian, 11. Modul Tambahan v0.3, 1. Gambaran Umum, 2. Lapisan, 3. Tahap Pipeline, 4. Sumber Data & Source Registry, 5. Orkestrasi, 6. Struktur Repo (+5 more)

### Community 18 - "ReportExporter"
Cohesion: 0.19
Nodes (8): Any, Path, Generates static HTML and JSON analytical reports into outputs/., Exports system analytical snapshots and statistics., Renders self-contained static HTML report for the 3 core targets., Exports analytical JSON snapshot., ReportExporter, Report export utilities.

### Community 19 - "Database"
Cohesion: 0.33
Nodes (3): Path, Seeds the 3 core locked assets from asset_master.csv., Seeds asset aliases from aliases.csv.

### Community 20 - "FinNews: Financial News Sentiment & Market Association System"
Cohesion: 0.15
Nodes (12): 1. Prasyarat & Instalasi, 2. Menjalankan Unit Test, 3. Eksplorasi Baseline Model (ML Offline), 4. Menjalankan Server API Backend, 🏛️ Arsitektur Sistem (3-Tier Layer), 🔒 Aturan Desain & Integritas Kuantitatif, FinNews: Financial News Sentiment & Market Association System, 🎯 Murni 3 Supervised (`XAU` / `RATE_UST` / `SPX`) (+4 more)

### Community 21 - "ParquetStore"
Cohesion: 0.20
Nodes (8): ParquetStore, Any, DataFrame, Path, Parquet storage helpers for bulk dumps and training datasets., Manages Parquet writes and reads for processed time series., Saves records to a Parquet file., Reads records from a Parquet file.

### Community 22 - "SCHEMA — Data Contracts"
Cohesion: 0.17
Nodes (11): 1. Enum, 2. Model Pipeline (Pydantic v2), 3. Output JSON (contoh), 4. Universe (`asset_master`), 5. Source Registry & Impact Graph, 6. Tabel Database (SQL), 7. Invarian (wajib dijaga validator), 8.1 Kontrak Role (+3 more)

### Community 23 - "Model Router: Cascade Routing ke Model Spesialis"
Cohesion: 0.20
Nodes (9): Arsitektur: dua tahap + fallback, Batasan yang diketahui, Cara menjalankan, Jejak audit, Masalah, Mengapa aturan bukti, bukan rata-rata, Model Router: Cascade Routing ke Model Spesialis, Tahap 1 — sumber dan kata kunci (+1 more)

### Community 24 - ".query_daily_sentiment"
Cohesion: 0.29
Nodes (4): date, Queries daily sentiment records between dates., Queries price records between dates., Retrieves joint sentiment and price series for a target.

### Community 25 - ".init_schema"
Cohesion: 0.29
Nodes (4): Initializes tables and indexes, lalu migrasi kolom yang menyusul., Menambah kolom baru pada DB lama. Idempoten dan aman diulang., Alias for init_schema., Connection

### Community 26 - ".route_article"
Cohesion: 0.12
Nodes (15): PriceRecord, SQLite database repository adhering to SCHEMA v0.5.0., Database and storage repository., Tests for SQLite database initialization, seeding, and operations., Verifies that asset_master and aliases are properly seeded., get_meta_summary returns real counts and version stamps for /api/meta., Time audit join degrades to real empties, never fake timestamps., Tests saving and querying daily sentiments. (+7 more)

### Community 27 - "fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX)"
Cohesion: 0.33
Nodes (5): fomc/ — Track FOMC-RoBERTa (target RATE_UST + SPX), Kerangka, Kontrak, Tugas track ini (M3, M6), Yang belum ada

### Community 28 - "xau/ — Track FinBERT-EMAS (target XAU)"
Cohesion: 0.33
Nodes (5): Kerangka, Kontrak, Tugas track ini (M2, M6), xau/ — Track FinBERT-EMAS (target XAU), Yang belum ada

### Community 29 - "StatResult"
Cohesion: 0.20
Nodes (9): 1. Mulai dari sini, bukan dari `ls -R`, 2. Peta cepat: di mana apa, 3. Aturan yang tidak boleh dilanggar, 4. Lingkup kerja per peran, 5. Perintah yang sering dipakai, 6. Konvensi commit, 7. Kondisi repository saat ini, 8. Saat ragu (+1 more)

### Community 30 - "dataset/ — Katalog Data"
Cohesion: 0.40
Nodes (4): dataset/ — Katalog Data, Dihapus 2026-10-11, Mapping label (beku), Sitasi

### Community 32 - "Theme & Splash — Bloomberg 70% × Claude 30%"
Cohesion: 0.40
Nodes (4): Catatan, Streamlit, Theme & Splash — Bloomberg 70% × Claude 30%, Web biasa

### Community 34 - "Model Research Notebooks"
Cohesion: 0.50
Nodes (3): Model Research Notebooks, Standar Output Artefak:, Struktur Notebook:

### Community 35 - "model/ — ML Research & Inference Pipeline (M1–M7)"
Cohesion: 0.50
Nodes (3): Aturan pembagian, model/ — ML Research & Inference Pipeline (M1–M7), Pemetaan Modul (M1–M7)

### Community 36 - "research/ — Ringkasan Paper Terkait"
Cohesion: 0.50
Nodes (3): 1. Paper Utama & Pendukung (Tersimpan di `research/papers/`), 2. Sintesis untuk Sidang Skripsi / TA, research/ — Ringkasan Paper Terkait

## Knowledge Gaps
- **212 isolated node(s):** `finews`, `1. Mulai dari sini, bukan dari `ls -R``, `2. Peta cepat: di mana apa`, `3. Aturan yang tidak boleh dilanggar`, `4. Lingkup kerja per peran` (+207 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Database` connect `.get_connection` to `schema.py`, `StatEngine`, `DailySentiment`, `TargetImpact`, `Database`, `.query_daily_sentiment`, `.init_schema`, `.route_article`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `ModelRouter` connect `ModelRouter` to `TargetImpact`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Why does `PriceRecord` connect `.route_article` to `StatEngine`, `TargetImpact`, `PriceRecord`, `.get_connection`, `.query_daily_sentiment`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `Database` (e.g. with `Basis` and `DailySentiment`) actually correct?**
  _`Database` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `TargetImpact` (e.g. with `DailyAggregator` and `Database`) actually correct?**
  _`TargetImpact` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 2 inferred relationships involving `DailySentiment` (e.g. with `DailyAggregator` and `Database`) actually correct?**
  _`DailySentiment` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 6 inferred relationships involving `TargetRouter` (e.g. with `Article` and `Basis`) actually correct?**
  _`TargetRouter` has 6 INFERRED edges - model-reasoned connections that need verification._