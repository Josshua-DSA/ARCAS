# DESIGN — Model, Scoring, Statistik & Antarmuka

> Status: Draft v0.8-p3 · GUI FastAPI+Vanilla+ECharts · murni 3 (XAU/RATE_UST/SPX) · tanpa LLM/RAG/agent · Melengkapi `ARCHITECTURE.md` (struktur) dan `SCHEMA.md` (kontrak data).

## 1. Prinsip

1. **Explainable**: setiap skor dapat ditelusuri ke teks & jalur sebab-akibat.
2. **Sederhana dulu**: komponen kompleks dipakai hanya bila mengalahkan pembanding sederhana.
3. **Konservatif**: inferensi tidak langsung → confidence rendah; lebih baik tidak memprediksi daripada menebak.
4. **Evaluasi jujur**: split waktu, tanpa kebocoran, koreksi uji berganda.

## 2. Taksonomi

### 2.1 Target (MURNI 3 — v2026-10-11-p3; 7 dicoret; IHSG dicoret; tambah/coret = bump universe_version)
| `asset_id` | Nama | Ticker | Kelas |
|---|---|---|---|
| `XAU` | Emas | `GC=F` | commodity |
| `RATE_UST` | Yield UST 10Y (`^TNX`/10) | `^TNX` | rate |
| `SPX` | S&P 500 | `^GSPC` | index |

Dicoret 2026-10-11: `OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`, `VIX`.
CPI/PCE, kebijakan bank sentral, employment = tema makro (§2.2), bukan target.

### 2.2 Tema makro (awal)
`rates_up/down`, `inflation_up/down`, `usd_up/down`, `risk_on/off`, `geopolitical_tension`, `tariff_up`, `supply_shock`.

### 2.3 Label
- `tone` (sentimen teks): `positive | neutral | negative`.
- `direction` (dampak ke target): `bullish | bearish | neutral | mixed`.
- Contoh beda: "USD menguat" → tone positif, tetapi `direction` untuk emas = bearish.

## 3. Model Sentimen

### 3.1 Baseline & pembanding [ML: M1-M4]
1. **TF-IDF + Logistic Regression** (baseline wajib, M1) — jalan dulu tiap dataset
   (gold 6882 pasca-DROP `none`; FOMC `split-combine-5768` 1939). Patokan murah
   sebelum transformer. Lapor wajib: F1 macro + kappa + confusion 3x3 + ECE.
   Lanjut FinBERT/FOMC-RoBERTa hanya bila kalahkan baseline bermakna
   (McNemar/bootstrap). Eksekusi di chat ML, bukan chat planning ini.
2. **Gold (`XAU`)**: FinBERT fine-tune ringan; mapping `Price Direction Up→positive, Down→negative, Constant→neutral` (kolom `none` diputus §3.4).
3. **FOMC (`RATE_UST`+`SPX`)**: `gtfintechlab/FOMC-RoBERTa`; mapping resmi `LABEL_1 Hawkish, LABEL_0 Dovish, LABEL_2 Neutral`.
4. **IndoBERT + terjemahan ID→EN MATI** 2026-10-11 (dataset ID dihapus).

### 3.2 Fusion (Track A — MATI 2026-10-11, dataset ID dihapus; arsip, jangan pakai)

**Arsip MATI — jangan implementasi.**

**Versi 1 — Late fusion (stacking), default MVP**
```
p_indo = softmax(IndoBERT(text_id))          # 3 prob
p_fin  = softmax(FinBERT(translate(text_id)))# 3 prob
x      = concat(p_indo, p_fin)               # 6 fitur (opsional + logit, panjang teks, sumber)
p_fuse = LogisticRegression(x)               # dilatih pada split validasi
```
- Latih meta-classifier dengan cross-validation (out-of-fold) agar tidak bocor.
- Bandingkan juga: rata-rata sederhana dan rata-rata berbobot (bobot di-tuning di validation).

**Versi 2 — Early fusion (opsional, bila data cukup)**
Concatenate embedding `[CLS]` kedua model → classification head → fine-tune bersama. Lebih berat dan rawan overfit pada 500–1.000 data.

**Versi 3 — Tanpa terjemahan (opsional)**
Continued pretraining IndoBERT pada korpus berita keuangan ID → fine-tune.

**Ablation wajib**: TF-IDF+LR vs FinBERT (gold) / FOMC-RoBERTa (FOMC). Laporkan F1 macro + McNemar/bootstrap + biaya & latensi. IndoBERT/fusion/terjemahan MATI 2026-10-11.

**Track B**: FinBERT langsung (opsional fine-tune ringan jika ada label); bandingkan dengan skor sentimen bawaan vendor API sebagai pembanding, bukan sebagai kebenaran.

### 3.3 Teks input
- Judul + N token pertama isi (atau judul saja jika isi panjang/noisy); panjang konfigurasi.
- Berita panjang → chunking, agregasi probabilitas (rata-rata/max-conf).

### 3.4 Putus `none` gold + adapter (beku 2026-10-11)
- `none` gold = **DROP** (bukan gabung ke `neutral`). Bukti: 1574 train + 394 test
  `none` semua `Up=0/Constant=0/Down=0`; sampel isi promosi/irrelevan. Gabung
  cemari kelas `Constant` murni (301 train). Hasil: train 6882
  (`positive` 3531 / `negative` 3050 / `neutral` 301), test 1720 (881/764/75).
- Adapter tunggal ikut SCHEMA (`backend/src/normalize/adapters.py`):
  gold `News→title`, `Dates(%d-%m-%Y)→published_at UTC`, `query_target=XAU`,
  dedup `article_id`; FOMC `sentence→title=body`, `published_at=None`,
  `year` audit, stance `LABEL_2/1/0→neutral/hawkish/dovish`, dual tone
  (`RATE_UST`: hawkish→positive/dovish→negative; `SPX` sebaliknya).
- FOMC terkunci 1 varian `split-combine-5768` (train 1939 setelah dedup dari
  1984: neutral 955/dovish 512/hawkish 472; test 495 dari 496: 244/129/122).
  Raw immutable, olahan via adapter saja.

## 4. Penentuan Target & Arah

### 4.1 Tag target
1. **Routing**: berita ditarik atas nama target tertentu → kandidat target.
2. **Kamus kata kunci per target** (tanpa NER emiten) → `basis=explicit` bila disebut langsung.
3. **Makro**: tema terdeteksi → 3 target lewat `impact_graph.yaml` (evaluasi statistik 3 supervised).

### 4.2 Arah (`direction`)
- **Explicit**: `direction` = `tone` terhadap entitas (positif → bullish).
- **Macro_factor**: `direction = sign(graph[theme→target]) × intensitas tema`; tema diekstrak (klasifier tema terlatih), bukan hard-code.
- **Sector_inferred**: DICORET MVP, jangan pakai.

`impact_graph.yaml` (contoh)
```yaml
version: 2026-10-11-p3   # selaras universe lock murni 3 (7 dicoret; IHSG dicoret); bobot hipotesis awal
themes:
  rates_down:
    - {target: XAU, sign: +1, weight: 0.8}
    - {target: SPX, sign: +1, weight: 0.4}
    - {target: RATE_UST, sign: -1, weight: 0.9}
  rates_up:
    - {target: XAU, sign: -1, weight: 0.7}
    - {target: RATE_UST, sign: +1, weight: 0.9}
  usd_up:
    - {target: XAU, sign: -1, weight: 0.7}
  risk_off:
    - {target: XAU, sign: +1, weight: 0.6}
    - {target: SPX, sign: -1, weight: 0.6}
  geopolitical_tension:
    - {target: XAU, sign: +1, weight: 0.7}
```
Bobot adalah **hipotesis awal**, bukan fakta; diuji lewat analisis statistik.

## 5. Confidence

```
base     = CAP[basis]                  # explicit=1.00, macro_factor=0.85
strength = f(prominence, materiality, n_evidence)
p        = calibrated max-prob (fusion/FinBERT)   # temperature scaling / isotonic
agree    = agreement(p_indo, p_fin) (Track A) | 1.0 (Track B)
raw      = 0.40*strength + 0.30*p + 0.15*agree + 0.15*(1-uncertainty)
conf     = min(base, raw) - penalties
penalties= rumor(0.20) + mixed_signal(0.15) + ambiguous_entity(0.15) + weak_source(0.10)
```
- Bobot & penalti di config, di-tuning pada validation set.
- Entitas hanya disebut sekilas → cap 0.55 walau `explicit`.
- Berita yang **sangat mengarah** ke satu target (disebut di judul, event material makro) → confidence tinggi (≥ 0.80 bila bukti kuat).

## 6. Agregasi & Analisis Statistik

### 6.1 Agregasi harian per target
- `score_t = mean(score_i)` (opsi: bobot sumber, bobot confidence, jumlah berita).
- Simpan `n_articles_t`. **Hari tanpa berita → `NaN`**; analisis memakai observasi yang valid (atau flag `has_news`), bukan nol.
- `effective_trading_date`: berita setelah tutup → hari bursa berikutnya (per timezone bursa).

### 6.2 Metrik pasar
Return harian per target; abnormal return vs benchmark relevan (`SPX` untuk XAU/RATE_UST, pasar luas untuk masing-masing); volatilitas (rolling std), perubahan volume.

### 6.3 Uji
| Uji | Detail |
|---|---|
| Korelasi | Pearson & Spearman pada lag 0..k hari |
| Regresi | `ret_t = a + b*sent_{t-l} + kontrol (ret_{t-1}, volume, ret_pasar) + e`; SE robust (HAC) |
| Granger | Apakah sentimen membantu memprediksi return; cek stasioneritas dulu |
| Event study | Abnormal return di sekitar berita bersentimen kuat; CAR [−1,+1], [0,+5] |
| Multiple testing | Koreksi Bonferroni / Benjamini–Hochberg atas 3 supervised×lag |
| Robustness | Split waktu, sub-sampel per sumber, ukuran efek + CI |

### 6.4 Peringatan dini (P2)
Definisikan alert (mis. sentimen < ambang & n_articles ≥ k) → evaluasi precision/recall, lead time, false alarm rate terhadap gejolak harga.

## 7. Dihapus (tanpa RAG/Agent)

Bagian ini dihapus pada v0.4. Scope bersih total: tanpa RAG, tanpa agent.

## 8. Antarmuka

### 8.1 CLI
```
newsimpact collect --since 24h [--track A|B]
newsimpact label export|import
newsimpact train --model indobert|finbert|fusion
newsimpact score --since 24h
newsimpact analyze --target XAU --lags 0-5
newsimpact report --target XAU --from 2025-01-01
```

### 8.2 Tampilan ringkas
```
Target: XAU   Tanggal: 2026-10-08   n_articles: 14
Sentimen harian: +0.42 (conf 0.81)   [explicit 6 | macro_factor 8]
Top berita: ...
Bukan nasihat investasi.
```

### 8.3 GUI Web Dashboard (FR-15)
Arsitektur terpisah: Backend FastAPI (REST JSON) + Frontend Vanilla HTML5/CSS/JS + Apache ECharts offline (zero-CDN, zero-Node). RAM server <50 MB.

- **Endpoints REST FastAPI (`backend/src/serve/app.py`)**:
  - `GET /api/universe`: Daftar 3 target (`XAU/RATE_UST/SPX`), status metadata, tanggal update terakhir.
  - `GET /api/series/{target}`: Data deret waktu gabungan `DailySentiment` vs `PriceRecord` (return, volume, close).
  - `GET /api/impacts/{target}`: Daftar bukti berita (`evidence.quote`, sumber, URL, tone, direction, confidence, tema makro).
  - `GET /api/stats/{target}`: Koefisien korelasi Spearman, regresi OLS HAC, p-value terkoreksi BH-FDR, Granger causality, CAR event study.
  - `GET /api/allocation`: Alokasi baseline profil dan simulasi pergeseran Tilt (total konstrain 100%).
  - `GET /api/persona/{article_id}`: Stance 5 persona (BUY/HOLD/SELL), kekuatan sinyal, dan narasi penjelasan template.
- **Frontend SPA Ringan (`frontend/GUI/`)**:
  - `templates/index.html`: Shell dokumen tanpa framework, dilayani static mount FastAPI di `/`.
  - `src/css/theme.css`: Token GUI ikut `frontend/GUI/THEME.md` v0.1 (adaptasi offline, zero-CDN): font Newsreader/Inter/JetBrains Mono via `@font-face` lokal `src/fonts/` (7 woff2 OFL), base `#F6F4F4`, text `#2C2727`, accent `#FF7517`, surface `#3E3939`, semantik up/down/hold + palet grafik §8.
  - `src/js/app.js`: Native `fetch()` ke endpoint `/api/...`, update grafik ECharts reaktif tanpa refresh halaman.
  - `src/js/echarts.min.js`: Berkas pustaka offline tersimpan lokal (zero internet dependency).
- **Fallback Snapshot**: CLI `report` tetap menyediakan opsi generator satu berkas HTML beku `outputs/report.html` untuk demonstrasi offline darurat tanpa server.

### 8.4 TUI Terminal (Bloomberg Style)
Antarmuka terminal interaktif (`frontend/TUI/`) berbasis Python Rich / Textual dengan tema visual konsisten (Technical Surface `#3E3939`, Accent `#FF7517`, Typography `#F6F4F4`). Navigasi keyboard-driven: tab hotkeys `1-5`, filter `/`, inspeksi sparkline deret waktu, tabel sentimen real-time, dan kartu Persona POV untuk workflow riset quant cepat tanpa membuka browser.

### 8.5 Sistem Desain & Visual Tokens (Proporsi 65/20/10/5)

Distribusi proporsi ketat untuk menghadirkan visual bersih editorial dengan filosofi hibrida:

#### Filosofi Desain Hibrida (70% Claude / 30% Bloomberg)
- **70% Claude**: Layout lapang, whitespace proporsional, tipografi elegan dan nyaman dibaca, serta fokus pada alur membaca narasi riset.
- **30% Bloomberg**: Struktur informasi padat bernilai tinggi, visualisasi data deret waktu presisi, metadata finansial tajam, dan aksen warna orange (`#FF7517`) yang tegas.

#### Token Warna & Proporsi
| Token / Peran | Nilai Hex | Proporsi | Keterangan & Penggunaan |
|---|---|---|---|
| **Background / Base** | `#F6F4F4` | 65% | Latar kanvas utama, kartu konten dominan, area baca terang |
| **Typography** | `#2C2727` | 20% | Heading, body text, garis tepi halus, teks tombol primer |
| **Technical Surface** | `#3E3939` | 10% | Panel kode/syntax, panel terminal/log, footer, wadah teknis |
| **Accent / Highlight** | `#FF7517` | 5% | Tombol utama, penanda seri aktif, badge pilihan, focus state |

Spesifikasi token lengkap (turunan terang/gelap, semantik, skala sentimen, palet grafik, state interaksi) ikut `frontend/GUI/THEME.md` v0.1. `theme.css` adaptasi offline (tanpa `@import` Google Fonts, tanpa Streamlit).

#### Tipografi GUI (ikut THEME.md §10)
| Peran | Font | Dipakai untuk |
|---|---|---|
| Narasi / heading | Newsreader 300–400 (fallback Georgia, serif) | Judul halaman, judul berita, ringkasan, rationale |
| UI | Inter 400/500/600 (fallback system-ui) | Menu, tombol, label, tab |
| Data | JetBrains Mono 400/500 (fallback ui-monospace) | Harga, skor, confidence, ticker, tabel, chip |

Angka pakai `tabular-nums`. Chip/label kecil mono kapital 11–12px `letter-spacing 0.06em`.

#### Warna Semantik GUI (ikut THEME.md §6)
| Makna | Latar terang | Panel gelap |
|---|---|---|
| Naik / Bullish / BUY | `#1A7F37` | `#56D364` |
| Turun / Bearish / SELL | `#CF222E` | `#FF7B72` |
| Netral / HOLD | `#6B6464` | `#BDB7B7` |
| Peringatan / Mixed | `#8A5A00` | `#FFB000` |
| Info | `#0969DA` | `#79B8FF` |

Wajib ikon + tanda + teks (`▲ +0.42`, `▼ −0.31`, `BUY/SELL/HOLD`), bukan warna saja. Oranye dilarang untuk arah data.

#### Pemetaan Elemen Antarmuka
| Bagian Antarmuka | Spesifikasi Visual |
|---|---|
| **Navbar** | Background off-white (`#F6F4F4`), teks deep charcoal (`#2C2727`), border bawah halus |
| **Hero / Introduction** | Background off-white (`#F6F4F4`), heading deep charcoal (`#2C2727`), aksen orange (`#FF7517`) |
| **Tombol Utama** | Background orange (`#FF7517`), teks deep charcoal (`#2C2727`), hover sedikit lebih gelap |
| **Tombol Sekunder** | Background transparan/off-white, border dan teks deep charcoal (`#2C2727`) |
| **Project / Target Cards** | Mayoritas off-white dengan border halus; aksen orange untuk target/proyek unggulan |
| **Expertise / Tech Stack** | Card off-white, badge orange (`#FF7517`), panel kode dark warm gray (`#3E3939`) |
| **Dashboard & Visualisasi Data** | Background terang (`#F6F4F4`), teks & grid gelap (`#2C2727`), orange (`#FF7517`) untuk seri/indikator aktif |
| **Footer** | Background dark warm gray (`#3E3939`), teks off-white (`#F6F4F4`), link aktif orange (`#FF7517`) |
| **Hover & Active State** | Orange (`#FF7517`) sebagai indikator; hindari mewarnai semua elemen sekaligus |

#### Aturan Kunci Hirarki Visual
1. **Anti-Orange Overuse**: Dilarang membuat semua card orange. Orange adalah aksen penarik perhatian (5%), bukan warna latar massal.
2. **Pembeda Konten Teknis**: Gunakan dark warm gray (`#3E3939`) khusus membedakan blok teknis (code, schema preview, CLI snippet, footer) dari area narasi data.

## 9. Evaluasi Sistem

| Aspek | Ukuran |
|---|---|
| Klasifikasi | F1 macro, precision/recall, confusion matrix, Cohen's kappa, perbandingan model |
| Penandaan target | Precision/recall tagging |
| Confidence | ECE, reliability diagram |
| Hubungan statistik | Koefisien, signifikansi terkoreksi, ukuran efek |
| Efisiensi | Biaya & latensi per 1.000 berita (termasuk terjemahan) |

## 10. Keterbatasan

- Korelasi sentimen–harga umumnya lemah; bukan kausalitas.
- Bias sumber dan gaya bahasa antarportal.
- Terjemahan dapat mengubah nuansa istilah keuangan.
- Impact graph adalah hipotesis kasar; tidak memodelkan ekspektasi pasar (berita yang sudah *priced-in*).
- Riwayat berita API gratis pendek.
- Sistem ini alat analisis, **bukan rekomendasi investasi**.

## 11. Allocation Tilt

### 11.1 Kelas aset
`BOND` (obligasi), `MUTUAL_FUND` (reksadana), `STOCK` (saham), `ETF`, `GOLD`. (Opsional: `CASH` sebagai penyangga; `BTC` dicoret 2026-10-11.)

### 11.2 Skor per kelas (`alloc_map.yaml`)

| Kelas | Sumber skor | Catatan |
|---|---|---|
| GOLD | skor target `XAU` | langsung |
| STOCK | skor `SPX` (IHSG dicoret 2026-10-11; emiten dicoret MVP) | langsung |
| ETF | skor `SPX` (terkunci) | langsung |
| BOND | **diturunkan dari tema makro** (`rates_down` +, `inflation_up` −, `risk_off` +, dst.) + berita obligasi/SBN bila ada | tidak ada sentimen langsung; sumber yield TBD |
| MUTUAL_FUND | campuran BOND & STOCK sesuai jenis (pasar uang / pendapatan tetap / campuran / saham) | komposisi di config |

`s_c ∈ [−1, 1]`, `conf_c ∈ [0, 1]` per kelas dihitung dari `TargetImpact` yang relevan (rata-rata berbobot confidence).

### 11.3 Rumus
```
raw_c   = base_c * exp(λ * s_c * conf_c)          # λ kecil (config), tilt halus
w_c     = raw_c / Σ raw                           # normalisasi → total 100%
w_c     = clip(w_c, min_c, max_c)  lalu renormalisasi iteratif (water-filling)
w_c     = base_c + clip(w_c - base_c, -Δmax, +Δmax)   # batas pergeseran per run (mis. ±5 pp)
jika conf_c < conf_min  → delta_c = 0
```
- Hasil dibulatkan (mis. 0,5 pp) dengan koreksi sisa agar **total tepat 100%**.
- Ada **opsi smoothing** terhadap alokasi sebelumnya untuk mengurangi turnover.

### 11.4 Preset profil (contoh, bisa diubah; total wajib 100%)

| Kelas | Konservatif | Moderat | Agresif | Contoh pengguna (dinormalisasi) |
|---|---|---|---|---|
| Obligasi | 60 | 40 | 20 | 55 |
| Reksadana | 15 | 15 | 10 | 10 |
| Saham | 5 | 15 | 30 | 10 |
| ETF | 10 | 20 | 30 | 15 |
| Emas | 10 | 10 | 5 | 10 |
| **Total** | 100 | 100 | 100 | 100 |

Angka di atas **ilustrasi**, bukan rekomendasi.

### 11.5 Output
Tabel baseline vs tilt vs alokasi baru, delta (pp), confidence per kelas, 1–2 kalimat alasan, dan flag `no_change` bila bukti lemah. Disclaimer wajib.

## 12. Persona POV

### 12.1 Persona awal (`personas.yaml`)

| Persona | Horizon | Aversi risiko | Ambang stance θ | Min. confidence | Karakter |
|---|---|---|---|---|---|
| Retail Investor | medium | sedang | 0,25 | 0,50 | Mudah terpengaruh judul; asimetris terhadap berita negatif |
| Day Trader | intraday–short | rendah | 0,15 | 0,40 | Sangat sensitif berita jangka pendek, fokus volatilitas |
| Fund Manager | short–medium | sedang | 0,30 | 0,65 | Butuh bukti kuat; mempertimbangkan makro & relatif ke benchmark |
| Long-term / Pension | long | tinggi | 0,45 | 0,75 | Abaikan berita sementara; fokus tema struktural |
| Risk Manager / Hedger | medium | sangat tinggi | 0,20 (sisi negatif) / 0,40 (positif) | 0,50 | Fokus risiko turun; lebih cepat ke SELL/lindung |

Parameter di atas adalah **hipotesis awal** yang perlu direview ahli domain.

### 12.2 Perhitungan stance (kode)
```
match   = horizon_match(news_horizon, persona.horizon)        # 0..1
raw     = score * confidence * match
if raw < 0: raw = raw * (1 + persona.loss_aversion)
stance  = BUY  jika raw ≥  θ_p  dan confidence ≥ conf_min_p
          SELL jika raw ≤ -θ_p  dan confidence ≥ conf_min_p
          HOLD selain itu
strength = min(1, |raw| / (2 * θ_p))
```
- `news_horizon` ditentukan dari tipe event → horizon (config): mis. earnings/rumor = short, kebijakan moneter = medium, regulasi/struktural = long.
- Persona dievaluasi per target utama berita (atau per kelas aset untuk tampilan alokasi).

### 12.3 Tampilan
```
Berita: "BI pangkas suku bunga 25 bps"
Persona               SPX       Obligasi   Emas
Retail Investor       🟢 BUY    🟢 BUY     ⚪ HOLD
Day Trader            🟢 BUY    ⚪ HOLD    ⚪ HOLD
Fund Manager          ⚪ HOLD   🟢 BUY     ⚪ HOLD
Long-term / Pension   ⚪ HOLD   🟢 BUY     ⚪ HOLD
Risk Manager          ⚪ HOLD   ⚪ HOLD    🔴 SELL
Simulasi sudut pandang. Bukan nasihat investasi.
```
Hijau = BUY, merah = SELL, abu = HOLD; tebal/opasitas = strength. Tooltip: alasan, horizon, confidence.

### 12.4 Evaluasi fitur
- **Konsistensi**: skor lebih bullish tidak boleh menghasilkan stance lebih SELL (uji monotonisitas).
- **Kepatuhan**: total alokasi = 100%, min/max terpenuhi, `Δmax` terpenuhi.
- **Stabilitas**: turnover harian alokasi.
- **Face validity**: review ahli/praktisi terhadap parameter persona & contoh.
- **Opsional**: backtest alokasi vs baseline statis — **demo terpisah**, bukan klaim validitas sentimen (lihat `PRD.md` §14.3).
