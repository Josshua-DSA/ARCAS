# RULES — Aturan Wajib Proyek

> Mengikat manusia **dan** AI coding assistant. Jika konflik dengan dokumen lain, `RULES.md` menang.
> Versi: v1.1-p3 · GUI FastAPI+Vanilla+ECharts · murni 3 (XAU/RATE_UST/SPX) · struktur 3-tier (model/backend/frontend) · tanpa LLM/RAG/agent

## 1. Aturan Domain

### 1.1 Definisi
- **tone**: nada sentimen teks (`positive | neutral | negative`).
- **direction**: dampak yang diharapkan pada **target** (`bullish | bearish | neutral | mixed`). Tone ≠ direction (mis. "USD menguat" positif untuk USD tetapi bearish untuk emas).
- Proyek ini mengukur **asosiasi statistik**, bukan prediksi harga dan bukan rekomendasi investasi.

### 1.2 `basis` dan batas confidence

| `basis` | Kondisi | Cap |
|---|---|---|
| `explicit` | Target disebut langsung dan berita membahas hal material tentangnya | 1.00 |
| `macro_factor` | Dampak via tema makro (impact graph) | 0.85 |
| `sector_inferred` | DICORET MVP (baris cadangan, jangan pakai) | 0.60 |

- Berita **sangat mengarah** ke satu target (disebut di judul/pembuka, event material: keputusan suku bunga, data inflasi/employment, OPEC, geopolitik) → `explicit`, confidence ≥ 0.80 bila bukti kuat & tidak ambigu.
- Entitas hanya disebut sekilas (daftar/perbandingan) → maksimum 0.55.
- Rumor ("kabarnya", sumber anonim) → kurangi ≥ 0.20 + `flag: rumor`.
- Sinyal bertentangan → `mixed` atau turunkan confidence; jangan dipaksa satu arah.
- Tidak ada jalur sebab-akibat yang bisa dijelaskan → **jangan output** prediksi.

### 1.3 Evidence & rationale
- Prediksi `explicit` wajib punya `evidence.quote` yang persis ada di teks.
- Rationale ≤ 2 kalimat; dilarang menambahkan fakta yang tidak ada di berita.

### 1.4 Target
- Routing + supervised murni 3 `asset_id` v2026-10-11-p3 (`XAU`, `RATE_UST`, `SPX`). 7 dicoret 2026-10-11 (`OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`, `VIX`). Di luar 3 → **ditolak**. Tambah/coret = bump `universe_version` + Changelog.
- Ambiguitas nama → resolve dengan konteks; bila tetap ambigu → turunkan confidence + `flag: ambiguous_entity`.
- Berita **makro** dirutekan ke semua target relevan menurut `impact_graph`.

### 1.5 Disclaimer
- Semua output (CLI, dashboard, laporan) wajib memuat: **"Bukan nasihat investasi."**
- Kata **BUY/SELL** hanya boleh muncul pada fitur **Persona POV** dan harus diberi label **"Simulasi sudut pandang"** + disclaimer di tampilan yang sama. Di luar fitur itu, dilarang memakai "beli/jual" sebagai rekomendasi.
- Dilarang frasa kepastian ("pasti naik", "pasti untung", "wajib beli").

## 2. Aturan Data

1. **Patuhi ToS/robots.txt** sumber. Jangan menyebarkan ulang teks berita; bila lisensi melarang, simpan metadata + skor + ringkasan.
2. Simpan **raw** apa adanya (immutable) terpisah dari data olahan.
3. `published_at` disimpan dalam UTC; konversi bursa memakai timezone eksplisit.
4. **Hari tanpa berita = `NaN`**, bukan 0.
5. Berita setelah jam tutup bursa → dihitung ke hari perdagangan berikutnya.
6. Kolektor harian harus berjalan sedini mungkin; log kegagalan sumber (`source_health`).
7. Batas API gratis (kuota, riwayat, hak pakai) **diverifikasi di situs resmi** sebelum diandalkan; jangan hard-code angka dari blog/tutorial.
8. Ticker Yahoo harus diuji (`yfinance`) sebelum masuk `asset_master`.
9. Konvensi hari efektif: XAU cut-off 00:00 UTC; RATE_UST/SPX ikut kalender US. Ditetapkan di config dan dicatat.
10. Dataset berlabel publik hanya dipakai bila ketersediaan & lisensinya terverifikasi.

## 3. Aturan Pelabelan

- Minimal **dua anotator** pada seluruh/subset data; ukur **Cohen's kappa**.
- Panduan pelabelan tertulis (`data/labeled/GUIDELINES.md`) dan dibekukan sebelum pelabelan massal.
- Dilarang pra-label otomatis; label murni manusia.
- Test set dikunci; tidak dipakai untuk tuning apa pun.

## 4. Aturan Model & Evaluasi

1. **Split terkunci 70/15/15 temporal per bahasa** (train < val < test); tidak ada kebocoran informasi masa depan.
   - Track ID: tanpa dataset berlabel beku (CNBC-IHSG dihapus 2026-10-11); bila anotasi baru dibuka, ikut pola sama 70/15/15 temporal group by article.
   - Track EN aktif: gold Sinha 10.570 (`dataset/gold_sinha/`, `cc-by-nc-nd-4.0`) + FOMC (`dataset/fomc/` 48 xlsx, `CC BY-NC 4.0`), split 70/15/15 temporal group by article/meeting. Pilih 1 seed FOMC saja (rekomendasi `split-combine` 5768).
   - Val pakai: threshold, temperature scaling, fusion weight, early stop. Fusion LR latih di val/OOF saja.
   - Test kunci sekali final; lapor F1 macro, kappa, confusion matrix, ECE.
2. Wajib baseline **TF-IDF + Logistic Regression jalan dulu** tiap dataset; komponen kompleks hanya dipakai bila mengalahkan pembanding sederhana bermakna (lihat `PRD.md` §9). Lapor wajib F1 macro + kappa + confusion 3x3 + ECE. Eksekusi ML di chat lain, bukan chat planning ini.
3. Metrik klasifikasi: **F1 macro**, precision, recall, confusion matrix, kappa; laporkan per sumber dan per track.
4. Fusion dilatih dengan **out-of-fold** predictions; meta-classifier tidak boleh melihat test set.
5. Ablation wajib: TF-IDF+LR vs FinBERT (gold) / FOMC-RoBERTa (FOMC); lapor F1 macro + McNemar/bootstrap. IndoBERT/fusion/terjemahan MATI 2026-10-11.
6. Catat **biaya & latensi** per 1.000 berita tiap model (termasuk terjemahan).
8. Confidence final **dihitung kode** dan dikalibrasi (ECE dilaporkan).
10. Seed tetap; versi model/universe/skema dicatat pada setiap hasil.

## 5. Aturan Analisis Statistik

1. Seluruh perhitungan statistik dijalankan oleh **kode deterministik** (pandas/statsmodels/scipy). Statistik inti wajib kode deterministik.
2. Cek stasioneritas sebelum uji Granger; gunakan SE robust (HAC) pada regresi.
3. **Koreksi uji berganda** (Bonferroni/BH-FDR) atas target × lag × metrik.
4. Laporkan **ukuran efek + CI + n_obs**, bukan hanya p-value.
5. Dilarang menarik klaim kausal dari korelasi/Granger; gunakan bahasa "berasosiasi dengan".
6. Sentimen tidak dinilai dari profit trading.
7. Kontrol minimal regresi: return sebelumnya, volume, return pasar.
8. Simpan setiap hasil dengan parameter lengkap & `code_version` agar dapat direproduksi.

## 6. Dihapus (tanpa LLM/RAG/Agent)

Scope v0.4 bersih total: tanpa LLM, tanpa RAG, tanpa agent.

## 7. Aturan Kode

- Python 3.11+, type hints wajib, `ruff` + `mypy` bersih sebelum merge.
- Batas antar-tahap memakai model Pydantic dari `SCHEMA.md`; dilarang `dict` mentah lintas modul.
- Logika scoring/confidence/agregasi = fungsi murni (mudah diuji); I/O dipisah.
- Tidak ada magic number: ambang, cap, bobot, penalti ada di config / YAML.
- Tidak ada secret di repo; `.env` + `.env.example`.
- Error tidak ditelan diam-diam: log terstruktur + status gagal.
- Async/batch untuk I/O; hormati rate limit.
- Notebook hanya untuk eksplorasi; logika final dipindah ke `src/`.
- Commit kecil, Conventional Commits.

## 8. Aturan Pengujian

- Unit test: dedupe, time-align (akhir pekan/libur/zona waktu), tagging/alias, confidence, agregasi (hari tanpa berita), invarian skema.
- Golden test: 30–50 berita contoh (ID & EN) dengan ekspektasi; perubahan model wajib menjaga ambang metrik.
- Test statistik: hasil pada data sintetis dengan efek diketahui.
- Test adversarial: rumor, berita ganda, nama ambigu, berita non-finansial.
- Test kontrak: output selalu valid terhadap schema.

## 9. Perubahan Dokumen & Skema

- Ubah `SCHEMA.md` → naikkan `schema_version`, tulis migrasi, update Changelog.
- Ubah cap confidence/aturan 1.2 → re-evaluasi & catat di Changelog di bawah.
- Dokumen `context/` adalah sumber utama; bila kode menyimpang, perbarui dokumen **atau** perbaiki kode.

## 9.1 Batas Role
ML: probabilitas + tema + kalibrasi usul. Backend: direction/confidence/agregasi/statistik/alloc/persona/CLI/store. Statistik inti hanya Backend.

## 10. Untuk AI Assistant yang Mengerjakan Repo Ini

1. Baca seluruh `context/` sebelum menulis kode.
2. Jangan mengarang ticker, kuota API, data harga, atau metrik; bila tidak tahu, katakan dan minta verifikasi.
3. Jangan menambah dependensi besar tanpa alasan tertulis.
4. Pertahankan struktur direktori di `ARCHITECTURE.md`.
5. Bila spesifikasi ambigu, ajukan pertanyaan atau catat asumsi di `PRD.md` §13.

## 11. Aturan Allocation Tilt & Persona POV (v0.3)

1. Keduanya adalah **simulasi analitis/edukatif**, bukan rekomendasi personal. Tidak boleh menyebut "sesuai profil Anda"/"Anda sebaiknya"; gunakan bahasa deskriptif ("simulasi profil moderat menunjukkan …").
2. **Stance persona dan alokasi dihitung kode** deterministik; penjelasan disusun template deterministik dari field terstruktur dan **tidak boleh mengubah** angka/stance.
3. Total alokasi **wajib 100%** (validasi saat load config dan saat output); batas min/max dan `Δmax` per run wajib dipatuhi.
4. Alokasi = baseline profil + tilt terbatas; **dilarang** menghasilkan alokasi dari nol berdasarkan satu berita.
5. Bukti lemah (`confidence < conf_min`) → `no_change`/HOLD; jangan memaksakan arah.
6. Obligasi, reksadana, ETF tidak punya sentimen langsung: skor harus ditandai **diturunkan** (`sources` terisi) dan confidence-nya dibatasi (cap seperti `macro_factor`).
7. Parameter persona, preset profil, λ, Δmax, dan ambang disimpan di YAML berversi (`params_version`); bukan hard-code.
8. Tampilan wajib: warna **hijau = BUY, merah = SELL, abu = HOLD**, ditambah **ikon/teks** (jangan hanya warna; aksesibilitas) dan disclaimer.
9. Evaluasi fitur bukan dengan profit trading. Backtest alokasi (jika ada) dilabeli **demo terpisah**, tidak dipakai untuk mengklaim validitas sentimen.
10. Bila produk akan dipublikasikan ke publik, **tinjau ulang aspek regulasi** (mis. batasan penyampaian saran investasi) sebelum rilis; ubah disclaimer sesuai kebutuhan.
11. Contoh/preset angka di dokumen adalah ilustrasi dan harus diberi label demikian.

## 11.1 Aturan Frontend (GUI Web & TUI)
1. GUI Web menggunakan stack: FastAPI (REST JSON) + Vanilla HTML/CSS/JS + ECharts offline lokal (tanpa CDN, tanpa Node.js/npm build). RAM backend <50 MB.
2. Fallback beku tetap wajib: generator CLI `report` harus mampu mengekspor snapshot `outputs/report.html` mandiri (JSON embed) untuk mitigasi risiko demo sidang.
3. TUI terminal (`frontend/TUI/`) berbasis Python Rich / Textual dengan navigasi keyboard-driven murni.
4. Layout visual: tren `score_mean` vs harga (hari kosong NaN = gap, bukan 0) + tabel bukti kutipan persis + tabel uji statistik (estimate, CI, p, p_adj, n_obs) + tab simulasi Allocation Tilt & Persona POV.
5. Total alokasi wajib lolos validasi 100% di server (Python) dan klien (JS). Warna + ikon/teks (BUY hijau, SELL merah, HOLD abu).
6. Disclaimer wajib di setiap tampilan layar: "Bukan nasihat investasi. Simulasi sudut pandang."
7. Dilarang keras memakai framework berat (Streamlit, Next.js) dan tooling Node.js. Server GUI web dibatasi pada FastAPI lokal mandiri.
8. Aturan Proporsi Visual & Filosofi 70/30:
   - **70% Claude**: Whitespace lapang, tata letak bernapas, tipografi nyaman dibaca, alur membaca narasi riset bersih.
   - **30% Bloomberg**: Struktur data padat presisi, visualisasi grafik kuantitatif, metadata finansial tajam, dan aksen orange `#FF7517` tegas.
   - **Token Warna 65/20/10/5**: Base off-white `#F6F4F4` (65%), Typography deep charcoal `#2C2727` (20%), Technical Surface dark warm gray `#3E3939` (10%), Accent orange `#FF7517` (5%).
   - Anti-Orange Overuse: Orange eksklusif untuk CTA utama, indikator fokus, dan penanda seri aktif terpilih. Dilarang mewarnai seluruh kartu dengan orange.
   - Surface `#3E3939` dikhususkan sebagai pembeda konten teknis (panel syntax, CLI, schema, footer).
   - **Spesifikasi detail ikut `frontend/GUI/THEME.md` v0.1**: font Newsreader (serif narasi) / Inter (sans UI) / JetBrains Mono (mono data, `tabular-nums`); semantik terang UP `#1A7F37` / DOWN `#CF222E` / HOLD `#6B6464` / WARN `#8A5A00` / INFO `#0969DA` dan padanan panel gelap; palet grafik §8; oranye dilarang untuk arah data.
   - **Aksesibilitas wajib**: teks putih di atas `--accent` dilarang; teks kecil beraksen pakai `--accent-text` (terang) / `--accent-text-on-dark` (gelap); tiap warna semantik wajib ikon + tanda + teks; chip BUY/SELL/HOLD label "Simulasi sudut pandang".

## Changelog Aturan
- v1.1-p3 — Murni 3 (`XAU/RATE_UST/SPX`): 7 dicoret total (OIL/CU/NG/BTC/USDIDR/DXY/VIX); data/backend/context/docs sync; `universe_version` 2026-10-11-p3.
- v1.0 — Fokus supervised 3 (`XAU/RATE_UST/SPX`): gold Sinha 10.570 + FOMC 48 xlsx lokal; Track A ID mati; 7 sisa router-only.
- v0.9 — PhraseBank 2.264 dihapus (topik Nordik perusahaan, bukan makro); `dataset/` kosong, label wajib manual baru.
- v0.8 — Universe 11→10 (IHSG + `^JKSE` dicoret); dataset IHSG + FNSPID dihapus; benchmark sisa PhraseBank EN.
- v0.7 — GUI Web kunci: FastAPI (REST JSON) + Vanilla JS + ECharts offline (zero-Node); fallback snapshot beku CLI report tetap didukung; TUI Rich.
- v0.6 — Frontend kunci: laporan HTML beku single-file vanilla + ECharts offline; Streamlit/Next.js dicoret artefak sidang.
- v0.5 — Universe LOCKED 11 target; emiten individual + XAG/NDX/DJI + SBN-single-name dicoret MVP; konvensi cut-off 24 jam eksplisit.
- v0.4 — Hapus total LLM/RAG/agent/prompt versioning; pra-label otomatis dilarang; explainer template deterministik.
- v0.3 — Tambah fitur Allocation Tilt & Persona POV; izin terbatas kata BUY/SELL pada Persona POV dengan label simulasi.
- v0.2 — Disesuaikan: dua track, FinBERT+IndoBERT, aturan statistik & pelabelan, universe komoditas/BTC/indeks AS/IDX.
- v0.1 — Draf awal.
