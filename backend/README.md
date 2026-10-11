# backend/ — Core Engine & Deterministik Pipeline (B1–B9)

Lingkup kerja Backend Engineer:
- `src/collect/`: Penarikan berita (`news-watch`, RSS) & harga harian 3 target inti (`XAU`, `RATE_UST`, `SPX`) via `yfinance`.
- `src/normalize/`: Pembersihan, deduping, cut-off UTC & penyelarasan kalender bursa (`effective_trading_date`).
- `src/tagging/`: Keyword matching & traversal `impact_graph.yaml` 7 tema makro.
- `src/store/`: Skema SQLite & Parquet (`TargetImpact`, `DailySentiment`, `PriceRecord`).
- `src/aggregate/`: Agregasi harian (mean sentimen; hari tanpa berita = NULL).
- `src/alloc/`: Mesin simulasi Allocation Tilt (total bobot 100%).
- `src/persona/`: Mesin simulasi 5 persona investor (POV berbasis aturan).
- `src/stats/`: Uji statistik deterministik (Spearman, OLS Newey-West HAC, Granger causality, CAR event study).
- `src/report/`: Ekspor payload JSON & generator artefak `outputs/report.html`.
- `tests/`: Unit test & sanity checks pipeline.

Konsumsi inferensi dari `model/weights/`, ekspor data beku ke `frontend/`.
