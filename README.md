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

| Asset ID     | Kelas Aset | Track | Nama Aset                 | Ticker Harga | Bursa | Zona Waktu       | Sesi Tutup |
| ------------ | ---------- | ----- | ------------------------- | ------------ | ----- | ---------------- | ---------- |
| `XAU`      | Commodity  | B     | Gold Spot / Futures       | `GC=F`     | CME   | America/New_York | 17:00      |
| `RATE_UST` | Rate       | B     | US 10-Year Treasury Yield | `^TNX`     | CBOE  | America/New_York | 15:00      |
| `SPX`      | Index      | B     | S&P 500 Index             | `^GSPC`    | SNP   | America/New_York | 16:00      |

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

> Kontributor baru: baca **[CONTRIBUTING.md](CONTRIBUTING.md)** — setup venv,
> konvensi commit, aturan yang tidak boleh dilanggar, dan cara memakai code
> graph. Ringkasan di bawah hanya jalur cepatnya.

### 1. Prasyarat & Instalasi

Gunakan Python 3.11+. Pasang dependensi:

```bash
python -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env            # isi kunci API yang Anda punya
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

#### Preload berita otomatis (07:00 WIB)

Server menyalakan penjadwal latar yang menarik berita dari eulerpool sekali
sehari pada **07:00 WIB**, lalu menjalankan rantai penuh
`eulerpool -> raw_articles -> articles -> impacts`. Tanpa ini, halaman hanya
berisi data lama sampai seseorang ingat menjalankan CLI.

Perilaku yang perlu diketahui:

| Situasi | Yang terjadi |
| --- | --- |
| Aplikasi hidup melewati 07:00 | Preload berjalan pada tick berikutnya (≤30 detik). |
| Aplikasi dinyalakan pukul 09:00 | Slot 07:00 yang terlewat **dikejar segera** (`trigger=startup_catchup`). |
| Aplikasi dinyalakan pukul 05:00 | Tidak mengejar apa pun; menunggu 07:00. |
| Restart berulang di hari yang sama | **Tidak** menarik ulang bila slot sudah `ok`/`no_new`. |
| Tarikan gagal | Status `failed`/`partial`; boleh dicoba lagi pada startup berikutnya. |
| Tidak ada berita baru | Status `no_new` — tetap dianggap selesai, tidak diulang. |

Karena `--reload` menyalakan proses berkali-kali, matikan penjadwal saat
pengembangan:

```bash
ARCAS_DISABLE_SCHEDULER=1 uvicorn backend.src.serve.app:create_app --factory --reload
```

Riwayat setiap run tersimpan di tabel `ingest_runs` dan bisa dibaca lewat:

```bash
curl http://localhost:8000/api/preload/status
```

Endpoint itu juga dipakai GUI untuk menampilkan cap "preload terakhir
&lt;tanggal&gt;", sehingga pengguna tahu seberapa tua data yang dilihat alih-alih
disuguhi berita karangan saat API mati.

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
