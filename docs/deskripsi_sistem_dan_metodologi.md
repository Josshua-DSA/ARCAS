# Deskripsi Sistem dan Metodologi: Analisis Sentimen Berita Finansial Makro

> Dokumen Spesifikasi Metodologi Proyek FInews (Financial News Sentiment & Market Association System)  
> Lokasi Dokumen: `docs/deskripsi_sistem_dan_metodologi.md`  
> Referensi Terkait: `context/PRD.md`, `context/ARCHITECTURE.md`, `context/DESIGN.md`, `context/RULES.md`, `context/SCHEMA.md`

---

## 1. Problem Framing

Solusi dipilih setelah masalah, metrik domain, dan metrik teknis terdefinisi secara terukur, bukan sebaliknya. Urutan metodologis: **identifikasi masalah nyata**, **perumusan objektif & metrik domain**, **penetapan metrik teknis**, kemudian **uji kecocokan solusi (component necessity test)** untuk memastikan setiap komponen memang diperlukan.

### 1.1 Masalah & Problem Statement

#### A. Konteks dan Masalah Nyata
Analis ekonomi, manajer investasi, dan peneliti finansial dibanjiri ratusan hingga ribuan artikel berita per hari dari berbagai portal berita finansial domestik maupun global. Dalam ekosistem pasar, informasi bergerak cepat, namun kapasitas kognitif manusia terbatas (*information overload*). Akibatnya, pelaku pasar kesulitan memfilter berita mana yang memuat sentimen material terhadap kondisi ekonomi makro dan mana yang sekadar kebisingan (*market noise*).

Ada dua pertanyaan mendasar yang ingin dijawab:
1. **Bagaimana arah nada berita (*tone*) dan arah dampak (*direction*) terhadap instrumen makro dari waktu ke waktu?**
2. **Apakah arah sentimen berita tersebut membawa kandungan informasi (*information content*) yang berasosiasi dengan pergerakan metrik pasar (return, volatilitas, volume)?**

Kedua pertanyaan ini merupakan masalah **klasifikasi teks multi-kelas (NLP)** dan **analisis asosiasi statistik empiris (ekonometrika)**, **bukan** prediksi harga langsung (*price prediction*) dan **bukan** rekomendasi investasi otomatis.

#### B. Problem Statement
> *"Bagaimana merancang sistem klasifikasi teks otomatis berbasis model bahasa domain finansial (IndoBERT & FinBERT) yang mampu mengekstraksi sentimen berita makro dwibahasa secara terkalibrasi, memetakan transmisi dampaknya secara deterministik ke dalam 11 aset makro global terkunci, serta menguji ada-tidaknya signifikansi hubungan statistik antara dinamika sentimen teks dengan pergerakan harga pasar tanpa mengandalkan model generatif berisiko halusinasi?"*

#### C. Pengguna Utama & Kebutuhan
- **Peneliti / Akademisi (Utama):** Membutuhkan dataset terstandarisasi, pipeline inferensi reproducible (seed terkunci, non-lookahead), dan metodologi ekonometrika yang valid dengan koreksi uji berganda.
- **Analis Pasar / Ekonom:** Memerlukan pemantauan tren sentimen agregat per kelas aset, perambatan isu makro (suku bunga, inflasi, komoditas), dan visualisasi terpadu pergerakan sentimen vs harga.
- **Pengembang / Kuantitatif:** Memerlukan kontrak data terstruktur (Pydantic), API data historis, dan antarmuka analitis deterministik berkecepatan tinggi.

---

### 1.2 Objektif, Metrik Domain, dan Metrik Teknis

| Objektif Domain | Metrik Domain | Metrik Teknis | Target / Ambang Batas |
|---|---|---|---|
| **Membaca arah berita dengan benar** | Kesesuaian label model dengan konsensus analis manusia | Macro F1-score, Precision/Recall per kelas, Cohen's kappa ($\kappa$), Confusion Matrix | Macro F1 $\ge 0.82$, $\kappa \ge 0.70$ terhadap anotator |
| **Keandalan probabilitas model** | Tingkat keyakinan model sebanding dengan akurasi empiris | Expected Calibration Error (ECE), Brier Score | ECE $\le 0.10$ pasca-kalibrasi suhu (*temperature scaling*) |
| **Pemantauan target makro** | Cakupan 11 aset makro dan hari perdagangan terpantau | Precision/Recall penandaan target, proporsi hari aktif dengan $\ge 1$ berita | Precision tag $\ge 0.90$, hari kosong ditandai `NaN` eksplisit |
| **Menguji nilai informasi sentimen** | Signifikansi hubungan sentimen dengan return/volatilitas/volume | Korelasi rank Spearman per lag ($t$ s.d. $t+5$), koefisien & p-value OLS Newey-West HAC, Uji Kausalitas Granger, CAR Event Study | $p < 0.05$ setelah koreksi Benjamini-Hochberg FDR |
| **Pencegahan bias data masa depan** | Integritas deret waktu (*zero lookahead bias*) | Validasi cut-off waktu perdagangan per bursa (UTC 00:00 untuk aset 24 jam) | 100% berita pasca-tutup bursa dialihkan ke $t+1$ |
| **Efisiensi komputasi** | Kecepatan inferensi dan biaya operasional rendah | Latensi per 1.000 berita, konsumsi RAM inferensi | Latensi $< 60$ detik / 1.000 artikel (GPU) atau $< 180$ detik (CPU), RAM $< 2$ GB |
| **Transparansi & auditabilitas** | Penjelasan keputusan dapat diverifikasi | Keberadaan kutipan bukti teks (*evidence span*), jalur graf sebab-akibat | 100% prediksi berlabel `explicit` memiliki kutipan teks persis |

*Catatan evaluasi: Skor F1 tinggi hanyalah prasyarat teknis. Keberhasilan domain ditentukan oleh validitas uji statistik dan kejelasan inferensi. Sentimen tidak dinilai dari profit trading untuk menghindari klaim kausalitas semu.*

---

### 1.3 Uji Kecocokan Solusi (Component Necessity Test)

Komponen arsitektur hanya dipertahankan apabila pembanding yang lebih sederhana terbukti tidak memadai:

| Komponen | Masalah yang Dijawab | Pembanding Sederhana | Syarat Dipakai dalam Sistem | Status Komponen |
|---|---|---|---|---|
| **TF-IDF + Logistic Regression** | Baseline klasifikasi teks cepat | Aturan leksikon / kata kunci | Selalu dipakai sebagai tolok ukur dasar (M1) | **Wajib (Baseline)** |
| **IndoBERT Fine-Tuned** | Memahami teks berita makro Bahasa Indonesia (Track A) | TF-IDF + Logistic Regression | Macro F1 IndoBERT mengungguli baseline secara signifikan ($> +5\%$) | **Terpilih (Track A)** |
| **FinBERT (Domain-Specific)** | Ekstraksi sentimen berita makro Bahasa Inggris (Track B) | General BERT / VADER | Menghasilkan separasi kelas finansial lebih tajam pada dataset benchmark | **Terpilih (Track B)** |
| **Late Fusion (Stacking)** | Integrasi sinyal IndoBERT dan FinBERT (via terjemahan) | IndoBERT tunggal | Uji signifikansi McNemar membuktikan fusion meningkatkan F1 di atas biaya latensi MT | **Terpilih (Track A Opt)** |
| **Mesin Statistik Deterministik** | Uji korelasi, OLS HAC, Granger, CAR | Tidak ada pengganti kode | Wajib kode murni deterministik (pandas/statsmodels/scipy) agar dapat direproduksi penuh | **Wajib Mutlak** |
| **LLM Generatif / RAG / Agent** | Otomasi narasi atau ekstraksi generatif | Pipeline kode terstruktur + template | **Dieliminasi (v0.4+)**: Berisiko halusinasi, latensi tinggi, non-deterministik, dan rawan lookahead bias | **Dicoret dari MVP** |
| **Graf Transmisi Makro (`impact_graph`)** | Pemetaan transmisi tema makro ke 11 aset | Rule hardcoded satu persatu | Memisahkan konfigurasi transmisi ekonomi ke format YAML deklaratif yang mudah diaudit | **Terpilih** |

---

## 2. Deskripsi Sistem

Sistem **FInews** adalah platform analitis kuantitatif terstruktur yang bertugas mengekstraksi nada sentimen berita ekonomi makro dalam dua bahasa (Bahasa Indonesia & Bahasa Inggris), memetakan arah dampaknya secara deterministik terhadap **11 Target Aset Makro Global Terkunci**, serta menguji hubungan statistik empiris antara sentimen agregat harian dengan dinamika pergerakan pasar.

### 2.1 Tujuan Sistem
1. Mengklasifikasikan sentimen artikel berita makro ke dalam 3 kelas: `positive`, `neutral`, `negative` dengan probabilitas terkalibrasi.
2. Memetakan dampak berita ke arah pasar (*direction*): `bullish`, `bearish`, `neutral`, atau `mixed` berdasarkan basis bukti eksplisit atau graf tema makro.
3. Menghitung deret waktu agregasi harian per aset dengan penanganan hari libur/kosong secara eksplisit (`NaN`).
4. Menjalankan pengujian statistik ekonometrika otomatis untuk mendeteksi apakah sentimen berita mendahului atau merefleksikan pergerakan return, volatilitas, dan volume aset.
5. Menyajikan visualisasi interaktif melalui Web GUI ringan dan Bloomberg-style Terminal UI (TUI) beserta simulasi alokasi portofolio multi-persona.

### 2.2 Prinsip Desain
- **Pemisahan Model Teks & Matematika Pasar:** Model Transformer (IndoBERT/FinBERT) murni bertindak sebagai pembaca teks (*text reader*). Seluruh agregasi, korelasi, regresi, uji Granger, pergeseran alokasi, dan penilaian persona dihitung 100% oleh kode deterministik.
- **Tanpa LLM Generatif / Nol Halusinasi:** Sistem bebas dari runtime generative LLM, RAG probabilistik, atau autonomous agents yang tidak deterministik.
- **Auditabilitas Penuh:** Setiap inferensi memiliki riwayat input mentah, hash SHA-256 artikel, stempel waktu UTC, bukti kutipan teks (*evidence quote*), dan versi model yang tercatat.

### 2.3 Cakupan 11 Target Makro Terkunci (Locked Universe v2026-10-09)

| Asset ID | Nama Instrumen | Kelas Aset | Ticker Harga | Bursa Utama | Zona Waktu | Jam Tutup |
|---|---|---|---|---|---|---|
| `XAU` | Emas Spot / Futures | Commodity | `GC=F` | CME | America/New_York | 17:00 |
| `OIL` | Minyak Mentah WTI | Commodity | `CL=F` | NYMEX | America/New_York | 17:00 |
| `CU` | Tembaga (Copper) | Commodity | `HG=F` | COMEX | America/New_York | 17:00 |
| `NG` | Gas Alam (Natural Gas) | Commodity | `NG=F` | NYMEX | America/New_York | 17:00 |
| `BTC` | Bitcoin USD | Crypto | `BTC-USD` | CCC | UTC | 00:00 |
| `USDIDR` | Kurs USD / Rupiah | FX | `IDR=X` | CCY | Asia/Jakarta | 16:00 |
| `DXY` | Indeks Dolar AS | FX | `DX-Y.NYB` | NYB | America/New_York | 17:00 |
| `RATE_UST` | Yield Obligasi US 10Y | Rate | `^TNX` | CBOE | America/New_York | 15:00 |
| `VIX` | Indeks Volatilitas CBOE | Volatility | `^VIX` | CBOE | America/New_York | 16:15 |
| `IHSG` | Indeks Harga Saham Gabungan | Index | `^JKSE` | IDX | Asia/Jakarta | 16:00 |
| `SPX` | S&P 500 Index | Index | `^GSPC` | SNP | America/New_York | 16:00 |

*(Catatan: Emiten saham individual dan komoditas minor dicoret dari lingkup MVP demi menjaga fokus makro).*

---

## 3. Arsitektur Sistem

Arsitektur FInews dibangun di atas pola **3-Tier Layered Architecture** yang modular, deterministik, dan dapat dijalankan secara terjadwal:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        TIER 1: INGESTION & DATA                        │
│  [Portal ID (CNBC/Bisnis)]  [Global Feed (Finnhub/RSS)]  [yfinance]   │
│            │                             │                    │        │
│            ▼                             ▼                    │        │
│    SHA-256 Deduplication         Language & Cleaning          │        │
│            │                             │                    │        │
│            └──────────────┬──────────────┘                    │        │
│                           ▼                                   │        │
│       Storage: SQLite (finews.db) + Parquet Cold Storage      │        │
└───────────────────────────┼───────────────────────────────────┼────────┘
                            │                                   │
┌───────────────────────────┼───────────────────────────────────┼────────┐
│                           ▼                                   │        │
│                 TIER 2: INFERENCE & ENGINES                   │        │
│  [Track A: IndoBERT / Fusion]     [Track B: FinBERT]          │        │
│            │                             │                    │        │
│            └──────────────┬──────────────┘                    │        │
│                           ▼                                   │        │
│                 Calibrated Sentiment Probabilities            │        │
│                           │                                   │        │
│       Target Router (aliases.csv + impact_graph.yaml)         │        │
│                           │                                   │        │
│                 Daily Aggregation (NaN handling)              │        │
│                           │                                   ▼        │
│                           └───────────────────► [Econometric Engine]   │
│                                                 - Spearman Lag         │
│                                                 - OLS Newey-West HAC   │
│                                                 - Granger Causality    │
│                                                 - BH-FDR Correction    │
│                                                       │                │
│                                         ┌─────────────┴─────────────┐  │
│                                         ▼                           ▼  │
│                                [Allocation Tilt]            [Persona]  │
└─────────────────────────────────────────┼───────────────────────────┼──┘
                                          │                           │
┌─────────────────────────────────────────┼───────────────────────────┼──┘
│                                         ▼                           ▼  │
│                        TIER 3: PRESENTATION SURFACE                    │
│   [FastAPI REST API]    [GUI: ECharts + Vanilla JS]   [TUI: Rich App]  │
│                         - RAM < 50 MB, Zero Node.js   - Bloomberg-style│
└────────────────────────────────────────────────────────────────────────┘
```

### Tabel Rincian Lapisan Arsitektur

| Lapisan | Fungsi Utama | Komponen & Teknologi | Keluaran Utama |
|---|---|---|---|
| **Tier 1: Pengumpulan & Penyimpanan** | Pengambilan artikel berkala, ingest harga pasar, deduplikasi idempotence, standarisasi waktu bursa | `requests`, `feedparser`, `yfinance`, SQLite (`finews.db`), Apache Parquet | `raw_articles`, `articles`, `market_prices` |
| **Tier 2: Pemrosesan Teks & Normalisasi** | Sanitasi regex HTML/ad, deteksi bahasa, mapping cut-off bursa UTC | Python standard, `re`, dateutil | Entitas `Article` bersih bertanggal bursa efektif |
| **Tier 2: Model Sentimen (NLP)** | Ekstraksi fitur teks, inferensi 3 kelas, kalibrasi suhu (*temperature scaling*) | PyTorch, HuggingFace Transformers (`IndoBERT`, `FinBERT`), Scikit-Learn | `ArticleSentiment` ($P_{pos}, P_{neu}, P_{neg}$, score $[-1, 1]$) |
| **Tier 2: Routing & Graf Makro** | Resolusi kata kunci eksplisit dan propagasi tema makro ke 11 aset | `aliases.csv`, `impact_graph.yaml` | `TargetImpact` (`direction`, `basis`, `confidence`) |
| **Tier 2: Mesin Ekonometrika** | Agregasi harian deret waktu, uji korelasi lag, regresi OLS robust, uji kausalitas | `pandas`, `statsmodels`, `scipy` | `StatResult` ($r_s$, koefisien OLS, p-value Granger, FDR) |
| **Tier 2: Simulasi Portofolio** | Simulasi kemiringan alokasi 6 kelas aset dan stance 5 persona investor | Formulasi matematika eksponensial deterministik | `AllocationResult` (total 100.0%), `PersonaStance` |
| **Tier 3: Antarmuka Penyajian** | REST API endpoints, Web GUI dashboard interaktif responsif, dan terminal TUI | FastAPI, Uvicorn, Vanilla HTML/CSS/JS, Apache ECharts offline, Python Rich | Port 8000 dashboard, Rich CLI screen, `report.html` |

---

## 4. Metodologi Rinci

### 4.1 Pengumpulan Data (Ingestion)
1. **Berita Bahasa Indonesia (Track A):** Ingest terjadwal portal CNBC Indonesia, Bisnis.com, dan Kontan menggunakan pustaka `news-watch` serta feed RSS Bank Indonesia.
2. **Berita Bahasa Inggris (Track B):** Ingest API Finnhub/Marketaux dan RSS rujukan (Federal Reserve, US BLS, EIA Energy, Kitco, CoinDesk, GDELT).
3. **Data Deret Waktu Pasar:** Pengambilan harga harian ($Open, High, Low, Close, Volume, Yield$) untuk 11 aset via `yfinance`.
4. **Idempotensi Penyimpanan:** Kunci unik berbasis `sha256(norm(title) + norm(body))[:16]` untuk mencegah duplikasi artikel.

### 4.2 Preprocessing & Temporal Alignment
1. **Pembersihan Teks:** Menghapus tag HTML, entitas unicode rusak, boilerplate disclaimer redaksi, dan nomor kontak iklan.
2. **Deduplikasi Semantik:** Mengeliminasi artikel duplikat menggunakan pencocokan hash SHA-256 dan kemiripan kosinus embedding teks $\ge 0.90$.
3. **Penyelarasan Kalender Bursa (*Non-Lookahead Temporal Alignment*):**
   - Aset beroperasi 24 jam (`XAU`, `OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`): Titik potong (*cut-off*) ditetapkan tepat pukul `00:00 UTC`.
   - Aset bursa berjadwal (`IHSG`, `SPX`, `RATE_UST`, `VIX`): Mengikuti jam penutupan bursa lokal masing-masing (misal: IHSG tutup pukul 16:00 WIB / 09:00 UTC).
   - **Aturan Non-Lookahead:** Berita yang terbit *setelah* jam tutup bursa secara otomatis dipetakan ke hari bursa efektif berikutnya ($t+1$). Tidak ada data masa depan yang boleh bocor ke inferensi hari ini.

### 4.3 Pelabelan dan Model Sentimen

#### A. Dataset Benchmark & Anotasi Manual
- **Benchmark Internasional:** Financial PhraseBank (4.840 kalimat finansial berlabel multi-anotator) dan FNSPID reduced (3.1 GB deret waktu berita finansial).
- **Anotasi Manual Bahasa Indonesia:** 500–1.000 artikel berita finansial makro diverifikasi secara independen oleh minimal 2 anotator manusia menggunakan panduan tertulis (`GUIDELINES.md`). Tingkat kesepakatan antar-anotator diukur menggunakan koefisien *Cohen's kappa* ($\kappa$).

#### B. Pipeline Model
1. **Baseline Model (M1):** Unigram & bigram TF-IDF dipasangkan dengan Logistic Regression teratur.
2. **Track A — IndoBERT (M2):** Model pre-trained `indolem/indobert-base-uncased` yang di-fine-tune untuk klasifikasi 3-kelas dengan *Weighted Cross-Entropy Loss* guna mengatasi ketidakseimbangan kelas (*class imbalance*).
3. **Track B — FinBERT (M3):** Model `ProsusAI/finbert` yang telah terlatih pada korpus bahasa finansial global.
4. **Track A Option — Late Fusion (M4):** Penggabungan vektor probabilitas `softmax` IndoBERT teks asli dengan `softmax` FinBERT (atas teks hasil terjemahan mesin ID $\rightarrow$ EN), dilatih menggunakan regresi logistik meta-classifier pada split validasi *out-of-fold*.

#### C. Kalibrasi Probabilitas & Skor Terstruktur
Probabilitas mentah dikalibrasi menggunakan metode *Temperature Scaling* untuk meminimalkan *Expected Calibration Error* (ECE). Skor sentimen kontinu dihitung:
$$\text{Score} = P(\text{Positive}) - P(\text{Negative}) \in [-1.0, +1.0]$$

Plafon tingkat keyakinan (*confidence cap*) dibatasi secara deterministik:
- Basis Bukti Langsung (`explicit`): Plafon keyakinan maksimum = $1.00$.
- Basis Inferensi Tema Makro (`macro_factor`): Plafon keyakinan maksimum = $0.85$.

### 4.4 Agregasi Sentimen Harian
Skor sentimen berita diagregasi menjadi indeks harian per aset:
$$S_{i, t} = \frac{\sum_{k=1}^{N_{i,t}} w_k \cdot \text{Score}_k}{\sum_{k=1}^{N_{i,t}} w_k}$$
Di mana $w_k$ adalah bobot kredibilitas sumber berita.  
**Aturan Hari Kosong:** Hari libur bursa atau hari tanpa berita yang relevan ditandai sebagai `NaN` eksplisit, **dilarang keras** diisi nilai $0$ agar tidak mendistorsi perhitungan korelasi statistik.

### 4.5 Analisis Ekonometrika Hubungan Sentimen & Pasar
Seluruh komputasi dijalankan secara deterministik menggunakan pustaka `statsmodels`, `scipy`, dan `pandas`:

1. **Uji Stasioneritas:** Uji Augmented Dickey-Fuller (ADF) pada return harga dan deret sentimen.
2. **Korelasi Spearman Lintas Lag:** Mengukur derajat asosiasi monotonik pada jeda waktu $t, t+1, \dots, t+5$:
   $$r_s = 1 - \frac{6 \sum d_i^2}{n(n^2 - 1)}$$
3. **Regresi Linear Robust (OLS Newey-West HAC):** Memodelkan return aset terhadap sentimen dengan mengendalikan return masa lalu dan volume perdagangan, menggunakan *Heteroskedasticity and Autocorrelation Consistent* (HAC) standard error:
   $$R_{i, t+1} = \alpha + \beta_1 S_{i, t} + \beta_2 R_{i, t} + \beta_3 \Delta \text{Vol}_{i, t} + \epsilon_t$$
4. **Uji Kausalitas Granger:** Menguji secara empiris apakah lag sentimen berita secara statistik menyediakan informasi tambahan untuk memproyeksikan return aset dibanding hanya mengandalkan lag return historis.
5. **Event Study (Cumulative Abnormal Return / CAR):** Mengukur abnormal return di sekitar jendela peristiwa lonjakan sentimen ekstrem ($[\tau_1, \tau_2]$).
6. **Koreksi Multi-Testing Benjamini-Hochberg (BH-FDR):** Menyesuaikan seluruh nilai $p$-value lintas 11 target dan 5 lag guna menekan laju penemuan palsu (*false discovery rate*):
   $$p_{(k)} \le \frac{k}{m} \cdot Q$$

### 4.6 Simulasi Portofolio Hilir

#### A. Allocation Tilt Engine
Menyesuaikan proporsi 6 kelas aset (Obligasi, Reksadana, Saham, ETF, Kripto, Emas) dari profil risiko baseline (Konservatif, Moderat, Agresif) berdasarkan sinyal sentimen makro.
- Menggunakan fungsi eksponensial deterministik terkendali (*bounded shift*).
- **Konstrain Absolut:** Total alokasi akhir terkonfirmasi wajib **tepat 100.0%**, dengan mematuhi batas alokasi minimum dan maksimum tiap kelas aset.

#### B. Persona POV Engine
Mengevaluasi sikap (*stance*) terhadap suatu berita: `BUY` (hijau), `HOLD` (abu-abu), atau `SELL` (merah) untuk 5 profil investor:
1. *Retail Investor* (sensitif terhadap narasi jangka pendek dan rumor).
2. *Day Trader* (fokus pada volatilitas instan dan momentum).
3. *Fund Manager* (berorientasi pada fundamental dan transmisi makro).
4. *Pension / Long-term Investor* (mengutamakan stabilitas dividen dan proteksi inflasi).
5. *Risk Manager / Hedger* (asimetri loss aversion tinggi, mengutamakan mitigasi downside risk).

*(Fitur ini murni simulasi analitis edukatif berdasar fungsi utilitas parameter, bukan anjuran finansial).*

### 4.7 Penyajian Antarmuka (Presentation Surfaces)
1. **Web GUI Dashboard:** Dibangun dengan arsitektur ringan tanpa Node.js (FastAPI backend + HTML5/CSS3 `#FF7517` aksen + Apache ECharts offline), konsumsi RAM $< 50$ MB.
2. **Terminal UI (TUI):** Antarmuka berbasis Python Rich berorientasi keyboard bergaya terminal Bloomberg, cocok untuk lingkungan server/headless.
3. **Laporan Statis:** Generator laporan HTML mandiri (`report.html`) yang membekukan data JSON ke dalam dokumen tunggal yang dapat dibuka secara offline.

---

## 5. Evaluasi Sistem

Evaluasi proyek diukur secara multidimensi:

| Aspek Evaluasi | Parameter & Metrik | Metode Pengukuran |
|---|---|---|
| **Klasifikasi Teks NLP** | Macro F1, Weighted Precision/Recall, Confusion Matrix | Evaluasi pada test set berbasis urutan waktu (*temporal split*) |
| **Kalibrasi Model** | Expected Calibration Error (ECE) | Perbandingan bin probabilitas model vs akurasi aktual (Guo et al., 2017) |
| **Agreement Anotator** | Cohen's kappa ($\kappa$) | Pengukuran inter-annotator agreement pada subset 200 artikel |
| **Korelasi Pasar** | Koefisien Spearman, Newey-West $t$-stat, p-value | Uji statistik deret waktu pada data pasar riil 2018–2026 |
| **Signifikansi Kausal** | F-test Granger causality | Perbandingan unrestricted vs restricted model regresi autoregresif |
| **Kepatuhan Konstrain Portofolio** | Validitas alokasi $\sum w_i = 100.0\%$ | Test suite otomatis unit test (`pytest`) pada batas batas ekstrem |
| **Efisiensi Komputasi** | Throughput artikel / detik, konsumsi memori | Profiling eksekusi backend dan latensi response endpoint FastAPI |

---

## 6. Batasan dan Risiko (Limitations & Risks)

1. **Bukan Rekomendasi Investasi:** Sistem murni instrumen komputasi riset. Terdapat disclaimer eksplisit di seluruh keluaran antarmuka dan laporan: *"Bukan nasihat investasi"*.
2. **Korelasi Bukan Kausalitas:** Adanya asosiasi statistik atau lolos uji Granger tidak membuktikan hubungan sebab-akibat mutlak di dunia nyata. Hasil disajikan dengan bahasa ilmiah terukur (*"berasosiasi dengan"*, bukan *"menyebabkan"*).
3. **Bias Sumber dan Gaya Bahasa:** Portal berita memiliki kecenderungan sensasionalisme (*clickbait*) atau keterlambatan publikasi dibandingkan arus data pasar berkecepatan tinggi (*high-frequency data*). Sistem memitigasi ini dengan pembobotan sumber kredibel.
4. **Lookahead Bias:** Resiko fatal kebocoran data masa depan dimitigasi ketat melalui pemisahan data temporal (*time-based split*) dan aturan cut-off bursa UTC yang konsisten.
5. **Kepatuhan Hukum & ToS:** Sistem menghormati `robots.txt` dan Terms of Service penyedia berita, hanya menyimpan metadata artikel, ringkasan, dan skor turunan di repositori publik.

---

## 7. Tahapan Pelaksanaan Proyek (Timeline 6 Minggu)

```
Minggu 1: Fondasi Skema, Ingestion & Data Registry
  ├── Finalisasi kontrak data Pydantic v2 (SCHEMA v0.5.0)
  ├── Konfigurasi asset_master.csv & aliases.csv 11 aset
  └── Implementasi collector harga yfinance & feeder berita

Minggu 2: Preprocessing Teks, Normalisasi & Baseline Model
  ├── Pembersihan regex, deduplikasi SHA-256, temporal cut-off
  ├── Anotasi subset data manual & validasi Cohen's kappa
  └── Pembangunan baseline model TF-IDF + Logistic Regression

Minggu 3: Deep NLP Modeling & Kalibrasi Probabilitas
  ├── Fine-tuning IndoBERT Track A dengan weighted cross-entropy
  ├── Konfigurasi inferensi FinBERT Track B
  ├── Pengujian Late Fusion meta-classifier
  └── Kalibrasi suhu model & evaluasi ECE

Minggu 4: Engine Routing Makro & Ekonometrika Deterministik
  ├── Implementasi graf transmisi tema makro (impact_graph.yaml)
  ├── Agregasi harian deret waktu dengan penanganan NaN eksplisit
  ├── Komputasi korelasi rank Spearman lintas lag
  └── Uji OLS Newey-West HAC, Granger causality & koreksi BH-FDR

Minggu 5: Simulasi Portofolio Hilir & REST API Backend
  ├── Engine Allocation Tilt dengan konstrain tepat 100.0%
  ├── Engine Persona POV untuk 5 profil investor
  └── Implementasi endpoint REST API FastAPI (/api/series, /api/stats)

Minggu 6: Antarmuka Visual (GUI/TUI), Evaluasi & Finalisasi Laporan
  ├── Integrasi dashboard Vanilla JS + Apache ECharts offline
  ├── Penyelesaian Bloomberg-style TUI berbasis Python Rich
  ├── Verifikasi unit test (pytest) & linter (ruff)
  └── Finalisasi dokumen metodologi dan materi presentasi
```

---

## 8. Penutup dan Pengesahan Dokumen

Dokumen metodologi ini mengikat seluruh implementasi kode pada repositori FInews. Setiap perubahan arsitektur, penambahan target alam semesta, atau perubahan kontrak skema wajib disertai pembaharuan versi dokumen terkait (`PRD.md`, `SCHEMA.md`, dan `RULES.md`).