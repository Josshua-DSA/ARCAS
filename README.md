# FinNews: Financial News Sentiment & Market Association System

Sistem analitis kuantitatif deterministik untuk sentimen berita keuangan makro EN (Track B), memetakan dampaknya ke **3 Target Tersupervisi Terkunci (`XAU`, `RATE_UST`, `SPX`)**, dan mengukur asosiasi statistik pasar serta simulasi alokasi portofolio multi-persona secara obyektif tanpa model generatif/halusinasi.

---

## 📌 Ringkasan Proyek

- **Fokus Domain**: Analisis sentimen berita keuangan makro terstruktur & uji ekonometrika empiris.
- **Batasan Alam Semesta**: Tepat 3 target tersupervisi (`XAU` gold Sinha human, `RATE_UST`+`SPX` FOMC human). Pensiun: `OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`, `VIX`, `IHSG`.
- **Pemisahan Ketat**:
  - Model Transformer/NLP bertindak murni sebagai pembaca teks (menghasilkan probabilitas 3-kelas: Positif, Netral, Negatif).
  - Seluruh inferensi agregasi, pergeseran portofolio (Allocation Tilt), stance persona, dan pengujian asosiasi pasar dihitung secara deterministik dengan matematika dan statistik baku (pandas, scipy, statsmodels).
  - Tanpa LLM runtime, tanpa agen generatif di jalur inferensi, tanpa halusinasi.

---

## 🏛️ Arsitektur Sistem (3-Tier Layer)

1. **Tier 1 — Data Ingestion & Storage**:
   - SQLite (`data/finews.db`) untuk metadata relasional, tabel skema baku v0.5.0, indeks deret waktu, dan log inferensi.
   - Parquet (`data/processed/`) untuk dump analitis skala besar.
   - Normalisasi teks deterministik (`article_id` berbasis SHA-256), deteksi bahasa, dan perataan kalender bursa non-lookahead (cut-off UTC 00:00).
2. **Tier 2 — NLP Inference & Econometric Engines**:
   - Model Sentimen: Baseline TF-IDF + LR, FinBERT (gold `XAU`), FOMC-RoBERTa (FOMC `RATE_UST`+`SPX`). Track A ID mati 2026-10-11.
   - Router Aset: Pemetaan eksplisit kata kunci (`aliases.csv`) dan perambatan tema makro (`impact_graph.yaml`).
   - Ekonometrika Pasar: Korelasi Spearman lintas lag (0..5), regresi OLS dengan galat baku Newey-West HAC, uji kausalitas Granger, dan Event Study Cumulative Abnormal Return (CAR) dengan koreksi multi-testing Benjamini-Hochberg (BH-FDR).
   - Allocation Tilt: Pergeseran alokasi eksponensial dengan konstrain ketat jumlah tepat 100.0%.
   - Persona POV: Evaluasi stance 5 profil investor (`retail`, `day_trader`, `fund_manager`, `pension`, `risk_manager`) dengan asimetri *loss aversion*.
3. **Tier 3 — Presentation Surface**:
   - REST API FastAPI (`backend/src/serve/app.py`).
   - TUI Terminal interaktif berbasis Python Rich (`frontend/TUI/`).
   - GUI Dashboard ringan berbasis Vanilla JS + Apache ECharts offline tanpa dependensi Node.js (`frontend/GUI/`).

---

## 🎯 Murni 3 Supervised (`XAU` / `RATE_UST` / `SPX`)

| Asset ID | Kelas Aset | Track | Nama Aset | Ticker Harga | Bursa | Zona Waktu | Sesi Tutup |
|---|---|---|---|---|---|---|---|
| `XAU` | Commodity | B | Gold Spot / Futures | `GC=F` | CME | America/New_York | 17:00 |
| `RATE_UST` | Rate | B | US 10-Year Treasury Yield | `^TNX` | CBOE | America/New_York | 15:00 |
| `SPX` | Index | B | S&P 500 Index | `^GSPC` | SNP | America/New_York | 16:00 |

Dicoret 2026-10-11: `OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`, `VIX`, plus `IHSG`; histori DB dipertahankan.

---

## 📁 Struktur Direktori

```
FInews/
├── .github/
│   └── workflows/
│       └── ci.yml               # GitHub Actions CI workflow (Python 3.11, pytest, ruff)
├── backend/
│   ├── src/
│   │   ├── aggregate/           # Agregasi harian (aturan: hari tanpa berita = NaN/NULL)
│   │   ├── alloc/               # Engine Allocation Tilt (konstrain jumlah tepat 100%)
│   │   ├── collect/             # Pengumpul data pasar yfinance & synthetic fallback
│   │   ├── normalize/           # Pembersihan teks, deteksi bahasa, perataan kalender bursa
│   │   ├── persona/             # Engine Persona POV (BUY/HOLD/SELL 5 profil investor)
│   │   ├── report/              # Generator snapshot HTML & JSON ke outputs/
│   │   ├── serve/               # REST API FastAPI (/api/universe, /api/series, dll.)
│   │   ├── stats/               # Engine statistik (Spearman, OLS HAC, CAR, BH-FDR)
│   │   ├── store/               # Repositori SQLite & Parquet store
│   │   ├── tagging/             # Router pemetaan aset & graf tema makro
│   │   └── schema.py            # Kontrak data Pydantic v2 (SCHEMA v0.5.0)
│   └── tests/                   # Test suite unit & integrasi backend
├── context/                     # Dokumen konteks & living specs (PRD, RULES, SCHEMA, dll.)
├── data/
│   ├── universe/
│   │   ├── asset_master.csv     # Spesifikasi 3 aset inti terkunci (core3)
│   │   └── aliases.csv          # Alias kata kunci untuk pemetaan eksplisit
│   ├── alloc_map.yaml           # Pemetaan kelas aset portofolio ke target skor
│   ├── alloc_profiles.yaml      # Profil alokasi baseline (konservatif, moderat, agresif)
│   ├── impact_graph.yaml        # Graf tema makro (rates, inflation, usd, geopolitical)
│   ├── personas.yaml            # Konfigurasi parameter 5 persona investor
│   └── source_registry.yaml     # Registry sumber berita & routing target
├── dataset/                     # gold_sinha/ (10.570 human) + fomc/ (48 xlsx human)
├── frontend/
│   ├── GUI/                     # Web Dashboard (Vanilla JS + ECharts offline)
│   └── TUI/                     # Terminal Dashboard (Python Rich)
├── model/
│   ├── evaluation/              # Metrik evaluasi model (F1 macro, ECE, Cohen's kappa)
│   ├── notebooks/               # Riset model offline & eksplorasi eksperimental
│   └── src/                     # Protokol inferensi & baseline TF-IDF + Logistic Regression
├── pyproject.toml               # Konfigurasi package, pytest, dan ruff
├── requirements.txt             # Dependensi Python inti
└── README.md                    # Dokumentasi utama proyek
```

---

## 🚀 Panduan Memulai (Quickstart)

### 1. Prasyarat & Instalasi
Gunakan Python 3.11+. Pasang dependensi:
```bash
pip install -r requirements.txt
```

### 2. Menjalankan Unit Test
Seluruh kontrak data Pydantic, operasi basis data SQLite, aturan konstrain 100% alokasi, dan baseline ML diuji otomatis:
```bash
pytest
```

### 3. Eksplorasi Baseline Model (ML Offline)
Jalankan eksperimen baseline TF-IDF + Logistic Regression pada modul riset:
```bash
python model/common/01_baseline_exploration.py
```

### 4. Menjalankan Server API Backend
Inisialisasi server REST API FastAPI:
```bash
uvicorn backend.src.serve.app:create_app --factory --host 0.0.0.0 --port 8000 --reload
```
Buka dokumentasi Swagger interaktif di `http://localhost:8000/docs`.

---

## 🔒 Aturan Desain & Integritas Kuantitatif

1. **Ketidakhadiran Berita Bukan Berarti Netral**:
   - Hari bursa tanpa berita menghasilkan nilai `score_mean = NULL` (NaN), bukan `0.0`.
   - Mengisi nilai 0 pada hari kosong merusak estimasi regresi dan korelasi ekonometrika.
2. **Pencegahan Lookahead Bias**:
   - Berita yang terbit setelah jam tutup bursa aset (`session_close`) dipetakan ke hari bursa efektif berikutnya.
3. **Konstrain Alokasi Portofolio**:
   - Total bobot alokasi setelah pergeseran Tilt dijamin secara deterministik bernilai tepat `100.0%`.
4. **Koreksi Multi-Testing**:
   - Seluruh pengujian statistik yang melibatkan multi-lag wajib melalui koreksi Benjamini-Hochberg FDR (`p_adjusted`).

---

## ⚠️ Peringatan Risiko Finansial (Disclaimer)

Sistem FinNews dibangun murni untuk tujuan penelitian akademis, rekayasa perangkat lunak finansial, dan edukasi analitis. Seluruh visualisasi, skor sentimen, simulasi alokasi portofolio, dan stance persona adalah simulasi matematis deterministik dan **BUKAN merupakan nasihat investasi, rekomendasi keuangan, atau ajakan transaksi efek berlisensi**.
