# PRD — Financial News Sentiment & Market Association System

> Status: Draft v0.7 · GUI FastAPI+Vanilla+ECharts · universe locked 12 target · tanpa LLM/RAG/agent · Bahasa: ID (istilah teknis tetap EN)
> Dokumen terkait: `ARCHITECTURE.md`, `DESIGN.md`, `SCHEMA.md`, `RULES.md`

## 1. Ringkasan

Sistem berbasis teks yang (1) mengklasifikasikan **sentimen berita finansial** (positif / netral / negatif) per berita, per target, dan per hari, lalu (2) **menguji secara statistik** apakah sentimen itu berhubungan dengan, atau mendahului, pergerakan pasar (return, abnormal return, volatilitas, volume).

Sistem **bukan** memprediksi harga dan **bukan** rekomendasi investasi. Statistik dihitung oleh kode deterministik (pandas, statsmodels); model BERT hanya membaca teks.

## 2. Universe Terkunci (v2026-10-09) + Dua Track Model

Universe dikunci 11 `asset_id`. Dilarang tambah target tanpa bump `universe_version`.

| `asset_id` | Nama | `price_ticker` (yfinance, verifikasi saat implementasi) | Kelas |
|---|---|---|---|
| `XAU` | Emas | `GC=F` | commodity |
| `OIL` | Minyak WTI (alt Brent `BZ=F`) | `CL=F` | commodity |
| `CU` | Tembaga | `HG=F` | commodity |
| `NG` | Gas alam | `NG=F` | commodity |
| `BTC` | Bitcoin | `BTC-USD` | crypto |
| `USDIDR` | USD/IDR | `IDR=X` | fx |
| `DXY` | Indeks dolar AS | `DX-Y.NYB` | fx |
| `RATE_UST` | Yield UST 10Y (`^TNX`/10) | `^TNX` | rate |
| `VIX` | Volatilitas US | `^VIX` | volatility |
| `IHSG` | IHSG | `^JKSE` | index |
| `SPX` | S&P 500 | `^GSPC` | index |

Dicoret MVP: `XAG` (duplikat XAU), `NDX`/`DJI` (duplikat SPX), `EUR/USD` (relevansi ID rendah), 45 emiten individual (beban NER), uranium/lithium/nikel (spot tidak ada di yfinance), SUN/SBSN/ORI/SBR + obligasi korporat/EM (sumber yield TBD, jadi lampiran riset bukan target). CPI/PCE, kebijakan bank sentral, employment = tema makro, bukan target.

| | Track A — berita ID | Track B — berita EN |
|---|---|---|
| Sumber | Bisnis, CNBC Indonesia, Kontan (`news-watch`), RSS BI | Finnhub/Marketaux/Alpha Vantage, RSS Fed/BLS/EIA/Kitco/CoinDesk, GDELT |
| Model sentimen | **IndoBERT + FinBERT (via terjemahan EN)**, late fusion | **FinBERT** (teks EN asli) |
| Target | Seluruh 11 universe (routing + impact graph) | Sama |
| Analisis | Korelasi, regresi, Granger, event study | Sama |

## 3. Masalah

- Analis tidak sanggup membaca ratusan berita per hari dan sulit tahu mana yang berkaitan dengan pasar.
- Dua pertanyaan inti: (a) bagaimana arah berita tentang suatu target dari waktu ke waktu, (b) apakah arah itu membawa informasi bagi pergerakan harga.
- Keduanya adalah masalah **klasifikasi teks + analisis asosiasi statistik**, bukan prediksi harga.

## 4. Tujuan & Non-Tujuan

### Goals
- G1. Klasifikasi sentimen 3 kelas per berita dengan `score [-1,1]` dan `confidence [0,1]` terkalibrasi.
- G2. Penandaan target (11 universe makro) dengan precision tinggi; target eksplisit → confidence tinggi.
- G3. Agregasi skor harian per target; hari tanpa berita ditangani eksplisit (bukan diisi 0).
- G4. Uji hubungan sentimen–pasar: korelasi per lag, regresi dengan kontrol, uji Granger, event study (CAR).
- G5. Penjelasan dapat ditelusuri (rationale + evidence span).
- G6. Perbandingan model terukur: TF-IDF+LR vs IndoBERT vs FinBERT(+terjemahan) vs Fusion.
- G7. Pengumpulan berita harian otomatis (karena API gratis minim riwayat).

### Non-Goals (v1)
- Bukan nasihat investasi personal, bukan eksekusi order, bukan prediksi harga numerik.
- Fitur **Allocation Tilt** dan **Persona POV** (§14) adalah **simulasi edukatif/analitis**, bukan rekomendasi untuk individu.
- Tidak dinilai dari profit trading (mengundang klaim prediksi yang bias).
- Bukan real-time ultra low-latency.

## 5. Pengguna & User Stories

| Persona | Kebutuhan |
|---|---|
| Peneliti / mahasiswa (utama) | Dataset berlabel, hasil uji statistik, laporan reproducible |
| Analis | Ringkasan sentimen per target + berita teratas |
| Developer | CLI/API/DB untuk integrasi |

1. Sebagai peneliti, saya mengumpulkan berita berbagai sumber ke satu skema terstandar.
2. Sebagai peneliti, saya melabeli 500–1.000 berita dan mengukur Cohen's kappa antar-anotator.
3. Sebagai peneliti, saya membandingkan model dengan F1 macro pada test set berbasis waktu.
4. Sebagai analis, saya melihat tren sentimen vs harga per target.
5. Sebagai analis, saya melihat hasil uji statistik (korelasi, Granger, event study) lengkap dengan signifikansi.

## 6. Functional Requirements

| ID | Requirement | Prioritas |
|---|---|---|
| FR-1 | Ingest berita: scraper ID, API/RSS EN, file CSV/JSON, input manual | P0 |
| FR-2 | Normalisasi, deteksi bahasa, deduplikasi (exact + embedding near-dup) | P0 |
| FR-3 | Penandaan target via `source_registry` (routing) + kamus kata kunci + impact graph | P0 |
| FR-4 | Penyelarasan waktu terbit dengan jam bursa; berita setelah tutup → hari bursa berikutnya | P0 |
| FR-5 | Klasifikasi sentimen Track A: IndoBERT + FinBERT(terjemahan) + fusion | P0 |
| FR-6 | Klasifikasi sentimen Track B: FinBERT | P0 |
| FR-7 | Baseline TF-IDF + Logistic Regression | P0 |
| FR-8 | Penentuan arah per target (`direction`) via entitas eksplisit atau impact graph makro | P0 |
| FR-9 | Confidence terkalibrasi + cap per `basis` (lihat `RULES.md`) | P0 |
| FR-10 | Agregasi harian per target (mean, opsi bobot sumber/jumlah berita, `n_articles`) | P0 |
| FR-11 | Analisis statistik: Pearson/Spearman per lag, regresi + kontrol, Granger, event study, koreksi uji berganda | P0 |
| FR-12 | Pengambilan harga & volume harian (yfinance) | P0 |
| FR-13 | Penyimpanan PostgreSQL/SQLite + Parquet, versi model/universe | P1 |
| FR-14 | CLI (`collect`, `label`, `train`, `score`, `analyze`, `report`) | P1 |
| FR-15 | GUI Web Dashboard (FastAPI REST JSON + Vanilla JS + CSS `#FF7517` + ECharts offline; RAM <50 MB, zero-Node) + opsi ekspor HTML beku CLI `report` | P1 |
| FR-17 | Orkestrasi harian (cron/Airflow/Prefect) | P2 |
| FR-18 | Peringatan dini (alert) sentimen ekstrem + evaluasi precision/recall/lead time | P2 |
| FR-19 | **Allocation Tilt**: usulan penyesuaian alokasi 6 kelas aset (Obligasi, Reksadana, Saham, ETF, BTC, Emas) dari berita, relatif terhadap baseline profil | P1 |
| FR-20 | Preset profil alokasi (Konservatif/Moderat/Agresif/Custom) dengan validasi total 100% & batas min/max per kelas | P1 |
| FR-21 | **Persona POV**: stance BUY (hijau) / HOLD (abu) / SELL (merah) dari 5 persona untuk satu berita | P1 |
| FR-22 | Penjelasan per persona & per kelas aset (template terstruktur, tanpa mengubah keputusan) | P1 |
| FR-23 | Atribut `news_horizon` per dampak (intraday/short/medium/long) | P1 |

## 7. Non-Functional Requirements

- **Reproducibility**: seed tetap, versi model/universe/skema pada setiap hasil.
- **Point-in-time**: tanpa kebocoran informasi masa depan; split berbasis waktu; universe point-in-time.
- **Biaya & latensi** dicatat per model per 1.000 berita (terjemahan + inferensi).
- **Auditability**: setiap prediksi dapat ditelusuri ke teks sumber.
- **Kepatuhan**: hormati ToS/robots.txt dan lisensi sumber berita.

## 8. Metrik Keberhasilan

Target angka ditetapkan **setelah baseline diukur** (jangan dipatok sebelum ada pembanding).

| Objektif | Metrik domain | Metrik teknis |
|---|---|---|
| Membaca arah berita | Kesesuaian dengan penilaian analis | F1 macro, Cohen's kappa model vs anotator, confusion matrix |
| Memantau sentimen per target | Cakupan target & hari | Precision/recall penandaan, proporsi hari dengan ≥1 berita, tingkat duplikasi |
| Nilai informasi sentimen | Hubungan dengan return/volatilitas/volume | Spearman per lag, koefisien & p-value regresi, uji Granger, CAR |
| Peringatan dini (P2) | Ketepatan sebelum gejolak | Precision/recall alert, lead time (hari), false alarm rate |
| Efisiensi | Waktu & biaya | Latensi & biaya per 1.000 berita |

## 9. Uji Kecocokan Komponen (komponen dipakai hanya jika pembanding sederhana gagal)

| Komponen | Pembanding sederhana | Syarat dipakai |
|---|---|---|
| IndoBERT fine-tuned | Kamus sentimen, TF-IDF+LR | F1 macro baseline di bawah target domain |
| FinBERT (+terjemahan) | IndoBERT saja | Fusion menaikkan F1 macro bermakna (uji signifikansi) di atas biaya terjemahan |
| Analisis statistik | — | Selalu dipakai (deterministik) |

## 10. Sumber Data (ringkas; detail di `ARCHITECTURE.md` §4)

- **Berita ID**: paket `news-watch` (Bisnis Indonesia, CNBC Indonesia, Kontan), scraping langsung (patuhi ToS), korpus `id_newspapers_2018` (opsional, domain umum, 2018).
- **Berita EN**: Finnhub, Marketaux, Alpha Vantage (cek batas gratis terbaru), RSS Fed/BLS/EIA/Kitco/CoinDesk, GDELT. `yfinance` `Ticker.news` hanya tambahan (hanya berita terbaru, tanpa riwayat).
- **Label**: dilabeli manual 400–600 berita (≥2 anotator, tanpa pra-label otomatis); benchmark publik terverifikasi di `dataset/` (Financial PhraseBank 4.840 baris EN, FNSPID reduced 3,1 GB EN, CNBC-IHSG IndoBERT ID); rujukan metodologi 15 paper di `research/papers/`.
- **Harga**: yfinance.

## 11. Fase

1. Pengumpulan data + dataset berlabel.
2. Baseline + fine-tuning IndoBERT; FinBERT + terjemahan; fusion.
3. Pemilihan model (baseline vs IndoBERT vs FinBERT vs fusion).
4. Analisis statistik sentimen vs pasar (Track A lalu B).
5. Dashboard.
6. Evaluasi akhir + laporan.

## 12. Risiko

| Risiko | Mitigasi |
|---|---|
| Korelasi sentimen–harga lemah / bukan kausalitas | Laporkan ukuran efek jujur; jangan klaim prediksi |
| Bias sumber & gaya bahasa antarportal | Fitur/bobot sumber, evaluasi per sumber |
| Kualitas terjemahan menurunkan FinBERT | Ablation; pilih MT terbaik; fallback IndoBERT saja |
| Riwayat berita API gratis pendek | Kumpulkan harian sedini mungkin |
| Lisensi/ToS sumber berita | Simpan metadata+skor+ringkasan; cek ketentuan |
| Hari tanpa berita memengaruhi statistik | `NaN` eksplisit, bukan 0 |
| Pengujian berganda (banyak target×lag) | Koreksi (Bonferroni/BH-FDR) |

## 13. Open Questions

1. Ketersediaan dataset berlabel publik (judul CNBC Indonesia) — perlu diverifikasi.
2. Metode terjemahan ID→EN (model MT lokal vs API).
3. Periode data (mis. 2024–2026). Universe dikunci v2026-10-09 (12 target di atas); emiten individual dicoret MVP.
4. Metode ekstraksi tema makro (klasifier tema terlatih).
5. Apakah dashboard masuk ruang lingkup tugas akhir atau fase lanjutan.
6. Daftar final 5 persona dan parameternya (horizon, toleransi risiko, ambang).
7. Baseline alokasi (preset) dan batas min/max per kelas — total harus 100%.
8. Sumber yield SBN/INDOGB + NAV reksadana TBD → lampiran riset, bukan target MVP. `RATE_UST` via `^TNX` terkunci; ETF acuan = SPX/IHSG.
9. Fitur ini untuk demo/edukasi saja, atau ada rencana dipublikasikan (berpengaruh pada disclaimer & regulasi)?

## 14. Fitur Tambahan (v0.3)

### 14.1 Allocation Tilt
Contoh: berita bernada dovish (suku bunga turun) → sistem menampilkan alokasi baseline vs alokasi yang disesuaikan.

| Kelas | Baseline | Tilt | Alokasi baru |
|---|---|---|---|
| Obligasi | 55% | +3 pp | 58% |
| Reksadana | 10% | 0 | 10% |
| Saham | 10% | 0 | 10% |
| ETF | 15% | −1 pp | 14% |
| BTC | 5% | −1 pp | 4% |
| Emas | 5% | −1 pp | 4% |
| **Total** | 100% | 0 | **100%** |

*(Angka ilustrasi. Tilt bersifat relatif: ia memindahkan porsi ke kelas dengan skor relatif tertinggi. Opsional: tambah kelas `CASH` sebagai penyangga bila total sinyal searah.)*

- Total **harus 100%**. (Contoh awal 60/10/10/20/5/5 berjumlah 110%, perlu dikoreksi; baseline di atas contoh 55/10/10/15/5/5.)
- Alokasi = **baseline profil + tilt kecil terbatas** dari skor berita, bukan alokasi dari nol.
- Metode deterministik & dapat dijelaskan (lihat `DESIGN.md` §11).

### 14.2 Persona POV (5 persona)
Satu berita → stance tiap persona: **BUY (hijau) / HOLD (abu) / SELL (merah)** beserta kekuatan dan alasan singkat. Persona awal (dapat diubah): **Retail Investor, Day Trader, Fund Manager, Long-term/Pension Investor, Risk Manager/Hedger**.

### 14.3 Catatan Penting
- Buy/Sell di sini = **simulasi sudut pandang** berdasar parameter persona, bukan saran untuk pengguna.
- Obligasi, reksadana, dan ETF **tidak punya sentimen berita langsung** di pipeline; skornya diturunkan dari tema makro & indeks/komoditas (lihat `DESIGN.md` §11.2). Sumber data obligasi/NAV reksadana **belum ditetapkan** (perlu verifikasi).
- PDF metodologi menyatakan sentimen **tidak dinilai dari profit trading**. Backtest alokasi (jika dibuat) adalah **demo terpisah**, tidak dipakai untuk menilai validitas sentimen.
- Metrik: kepatuhan batas (total 100%, min/max), stabilitas/turnover, uji konsistensi persona (monoton), review kewajaran oleh ahli domain.
