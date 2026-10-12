# PRD — Financial News Sentiment & Market Association System

> Status: Draft v0.8-p3 · GUI FastAPI+Vanilla+ECharts · murni 3 (XAU/RATE_UST/SPX) · tanpa LLM/RAG/agent · Bahasa: ID (istilah teknis tetap EN)
> Dokumen terkait: `ARCHITECTURE.md`, `DESIGN.md`, `SCHEMA.md`, `RULES.md`

## 1. Ringkasan

Sistem berbasis teks yang (1) mengklasifikasikan **sentimen berita finansial** (positif / netral / negatif) per berita, per target, dan per hari, lalu (2) **menguji secara statistik** apakah sentimen itu berhubungan dengan, atau mendahului, pergerakan pasar (return, abnormal return, volatilitas, volume).

Sistem **bukan** memprediksi harga dan **bukan** rekomendasi investasi. Statistik dihitung oleh kode deterministik (pandas, statsmodels); model BERT hanya membaca teks.

## 2. Universe Terkunci (v2026-10-11, fokus supervised v2026-10-11) + Satu Track Model

Routing murni 3 `asset_id` v2026-10-11-p3 (7 dicoret 2026-10-11: `OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`, `VIX`; IHSG dicoret 2026-10-11). **Evaluasi supervised 3 target** (gold + FOMC cover, §10). Dilarang tambah target tanpa bump `universe_version`.

| `asset_id` | Nama | `price_ticker` (yfinance, verifikasi saat implementasi) | Kelas | Supervised |
|---|---|---|---|---|
| `XAU` | Emas | `GC=F` | commodity | ✅ Sinha gold 10.570 headline human |
| `RATE_UST` | Yield UST 10Y (`^TNX`/10) | `^TNX` | rate | ✅ FOMC hawkish/dovish human |
| `SPX` | S&P 500 | `^GSPC` | index | ✅ FOMC sama, arah balik |
| Dicoret 2026-10-11 (bukan supervised, bukan router): `OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`, `VIX`. |

Dicoret MVP: `XAG` (duplikat XAU), `NDX`/`DJI` (duplikat SPX), `EUR/USD` (relevansi ID rendah), 45 emiten individual (beban NER), uranium/lithium/nikel (spot tidak ada di yfinance), SUN/SBSN/ORI/SBR + obligasi korporat/EM (sumber yield TBD, jadi lampiran riset bukan target). CPI/PCE, kebijakan bank sentral, employment = tema makro, bukan target.

| | Track A — berita ID (MATI 2026-10-11) | Track B — berita EN (AKTIF) |
|---|---|---|
| Sumber | ~~Bisnis, CNBC Indonesia, Kontan~~ (dataset ID dihapus) | Gold headlines (Sinha) + FOMC docs + RSS Fed/EIA/Kitco + yfinance harga |
| Model sentimen | — | **TF-IDF+LR baseline → FinBERT/FOMC-RoBERTa** per dataset (§10) |
| Target | — | murni 3 supervised |
| Analisis | — | Korelasi, regresi, Granger, event study (3 supervised) |

## 3. Masalah

- Analis tidak sanggup membaca ratusan berita per hari dan sulit tahu mana yang berkaitan dengan pasar.
- Dua pertanyaan inti: (a) bagaimana arah berita tentang suatu target dari waktu ke waktu, (b) apakah arah itu membawa informasi bagi pergerakan harga.
- Keduanya adalah masalah **klasifikasi teks + analisis asosiasi statistik**, bukan prediksi harga.

## 4. Tujuan & Non-Tujuan

### Goals
- G1. Klasifikasi sentimen 3 kelas per berita dengan `score [-1,1]` dan `confidence [0,1]` terkalibrasi.
- G2. Penandaan target (3 universe makro) dengan precision tinggi; target eksplisit → confidence tinggi.
- G3. Agregasi skor harian per target; hari tanpa berita ditangani eksplisit (bukan diisi 0).
- G4. Uji hubungan sentimen–pasar: korelasi per lag, regresi dengan kontrol, uji Granger, event study (CAR).
- G5. Penjelasan dapat ditelusuri (rationale + evidence span).
- G6. Perbandingan model terukur: TF-IDF+LR vs FinBERT (gold) / FOMC-RoBERTa (FOMC).
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
| FR-5 | ~~Track A ID: IndoBERT~~ — MATI 2026-10-11 | P3 |
| FR-6 | Klasifikasi sentimen EN: FinBERT (gold) / FOMC-RoBERTa (FOMC) | P0 |
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
| FR-19 | **Allocation Tilt**: usulan penyesuaian alokasi 5 kelas aset (Obligasi, Reksadana, Saham, ETF, Emas; BTC dicoret 2026-10-11) dari berita, relatif terhadap baseline profil | P1 |
| FR-20 | Preset profil alokasi (Konservatif/Moderat/Agresif/Custom) dengan validasi total 100% & batas min/max per kelas | P1 |
| FR-21 | **Persona POV**: stance BUY (hijau) / HOLD (abu) / SELL (merah) dari 5 persona untuk satu berita | P1 |
| FR-22 | Penjelasan per persona & per kelas aset (template terstruktur, tanpa mengubah keputusan) | P1 |
| FR-23 | Atribut `news_horizon` per dampak (intraday/short/medium/long) | P1 |

## 7. Non-Functional Requirements

- **Reproducibility**: seed tetap, versi model/universe/skema pada setiap hasil.
- **Point-in-time**: tanpa kebocoran informasi masa depan; split berbasis waktu; universe point-in-time.
- **Biaya & latensi** dicatat per model per 1.000 berita (inferensi).
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
| FinBERT (gold) | TF-IDF+LR | F1 macro + kappa + confusion 3x3 + ECE; dipakai hanya bila F1 macro bermakna di atas baseline (McNemar/bootstrap) |
| FOMC-RoBERTa (FOMC) | TF-IDF+LR | Sama; eksekusi ML di chat lain, bukan chat planning ini |
| Analisis statistik | — | Selalu dipakai (deterministik) |

## 10. Sumber Data (ringkas; detail di `ARCHITECTURE.md` §4)

- **Gold `XAU`** (`dataset/gold_sinha/`, 976K): `SaguaroCapital/sentiment-analysis-in-commodity-market-gold` (`cc-by-nc-nd-4.0`, `arxiv:2009.04202`), train 8.456 + test 2.114 parquet, kolom `Dates/URL/News/Price Direction Up/Constant/Down/Asset Comparision/Past Information/Future Information/Price Sentiment`. Train: positive 3.531 / negative 3.050 / none 1.574 / neutral 301; null 0, dup 0.
- **FOMC `RATE_UST`+`SPX`** (`dataset/fomc/`, 2,9M, `CC BY-NC 4.0`, Shah et al. ACL 2023): 24 xlsx train + 24 test, seed `5768/78516/944601`, varian `combine/mm/pc/sp/split-combine`. Mapping resmi `LABEL_1 Hawkish, LABEL_0 Dovish, LABEL_2 Neutral`. `combine-train-5768` 1.903 (neutral 929/dovish 498/hawkish 476), test 476; tahun 1996–2022.
- **Live/produksi**: RSS Fed/EIA/Kitco + yfinance (`GC=F`, `^TNX`, `^GSPC`); API gratis (Finnhub/Marketaux/Alpha) opsional, `news-watch`/scraper ID MATI.
- **Label**: dua dataset human publik lokal (`dataset/gold_sinha/` 10.570 + `dataset/fomc/` 48 xlsx, §10); tanpa anotasi manual baru; tanpa pra-label otomatis; rujukan metodologi 15 paper di `research/papers/`.
- **Harga**: yfinance.

## 11. Fase

1. Pengumpulan data + dataset berlabel.
2. Baseline TF-IDF+LR per dataset; fine-tune ringan FinBERT/FOMC-RoBERTa.
3. Pemilihan model (baseline vs transformer per dataset).
4. Analisis statistik sentimen vs pasar (3 supervised: `GC=F`, `^TNX`, `^GSPC`).
5. Dashboard.
6. Evaluasi akhir + laporan.

## 12. Risiko

| Risiko | Mitigasi |
|---|---|
| Korelasi sentimen–harga lemah / bukan kausalitas | Laporkan ukuran efek jujur; jangan klaim prediksi |
| Bias sumber & gaya bahasa antarportal | Fitur/bobot sumber, evaluasi per sumber |
| ~~Kualitas terjemahan~~ — MATI (Track A hapus) | — |
| Riwayat berita API gratis pendek | Kumpulkan harian sedini mungkin |
| Lisensi/ToS sumber berita | Simpan metadata+skor+ringkasan; cek ketentuan |
| Hari tanpa berita memengaruhi statistik | `NaN` eksplisit, bukan 0 |
| Pengujian berganda (banyak target×lag) | Koreksi (Bonferroni/BH-FDR) |

## 13. Open Questions

1. ~~Dataset berlabel (CNBC-IHSG + PhraseBank + FNSPID)~~ — DICORET 2026-10-11 (bukan makro / mikro single-ticker); kini gold Sinha 10.570 + FOMC 48 xlsx lokal (§10).
2. ~~Metode terjemahan ID→EN~~ — MATI 2026-10-11 (Track A hapus).
3. Periode data: gold 2000–2021 (kolom `Dates`), FOMC 1996–2022 (kolom `year`); split temporal group by article/meeting. Routing + supervised murni 3 v2026-10-11-p3; emiten individual dicoret MVP.
4. Metode ekstraksi tema makro (klasifier tema terlatih).
5. Apakah dashboard masuk ruang lingkup tugas akhir atau fase lanjutan.
6. Daftar final 5 persona dan parameternya (horizon, toleransi risiko, ambang).
7. Baseline alokasi (preset) dan batas min/max per kelas — total harus 100%.
8. Sumber yield SBN/INDOGB + NAV reksadana TBD → lampiran riset, bukan target MVP. `RATE_UST` via `^TNX` terkunci; ETF acuan = SPX.
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
| Emas | 10% | −2 pp | 8% |
| **Total** | 100% | 0 | **100%** |

*(Angka ilustrasi. Tilt bersifat relatif: ia memindahkan porsi ke kelas dengan skor relatif tertinggi. Opsional: tambah kelas `CASH` sebagai penyangga bila total sinyal searah.)*

- Total **harus 100%**. (Baseline contoh 55/10/10/15/10 berjumlah 100%; BTC dicoret 2026-10-11.)
- Alokasi = **baseline profil + tilt kecil terbatas** dari skor berita, bukan alokasi dari nol.
- Metode deterministik & dapat dijelaskan (lihat `DESIGN.md` §11).

### 14.2 Persona POV (5 persona)
Satu berita → stance tiap persona: **BUY (hijau) / HOLD (abu) / SELL (merah)** beserta kekuatan dan alasan singkat. Persona awal (dapat diubah): **Retail Investor, Day Trader, Fund Manager, Long-term/Pension Investor, Risk Manager/Hedger**.

### 14.3 Catatan Penting
- Buy/Sell di sini = **simulasi sudut pandang** berdasar parameter persona, bukan saran untuk pengguna.
- Obligasi, reksadana, dan ETF **tidak punya sentimen berita langsung** di pipeline; skornya diturunkan dari tema makro & indeks/komoditas (lihat `DESIGN.md` §11.2). Sumber data obligasi/NAV reksadana **belum ditetapkan** (perlu verifikasi).
- PDF metodologi menyatakan sentimen **tidak dinilai dari profit trading**. Backtest alokasi (jika dibuat) adalah **demo terpisah**, tidak dipakai untuk menilai validitas sentimen.
- Metrik: kepatuhan batas (total 100%, min/max), stabilitas/turnover, uji konsistensi persona (monoton), review kewajaran oleh ahli domain.
