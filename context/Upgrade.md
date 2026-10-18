# Upgrade UI FInews

> **Versi:** 1.2.0  
> **Tanggal:** 2026-10-18  
> **Workstream:** FInews — GUI/TUI auditability-first  
> **Status:** Rencana; bukan klaim implementasi selesai  
> **Sumber utama:** `PRD.md`, `RULES.md`, `SCHEMA.md`, `ARCHITECTURE.md`, `DESIGN.md`, implementasi GUI/API aktif, dan 15 paper di `research/papers/`

## 1. Tujuan

Meningkatkan UI FInews agar peneliti dapat menjawab tiga pertanyaan tanpa menebak:

1. Data dan skor ini berasal dari mana?
2. Bagaimana berita disejajarkan dengan sesi pasar dan lag analisis?
3. Seberapa kuat, terkalibrasi, dan dapat direproduksi hasilnya?

UI tetap menjelaskan **asosiasi historis**, bukan prediksi harga atau rekomendasi investasi.

## 2. Kondisi UI Saat Ini

GUI aktif sudah memiliki:

- tab dinamis untuk `XAU`, `RATE_UST`, dan `SPX`;
- grafik harga versus sentimen untuk 30/90/180 hari;
- tabel statistik ringkas;
- daftar bukti berita dan filter arah;
- simulasi Allocation Tilt dan Persona POV;
- status API, state loading/kosong/galat, fallback ilustrasi berlabel;
- disclaimer permanen dan warna semantik yang disertai ikon/teks.

Celah utama bukan kurangnya panel, tetapi kurangnya **provenance, audit waktu, kualitas data, dan konteks evaluasi model**.

## 3. Struktur Halaman yang Direkomendasikan

Gunakan **empat halaman HTML terpisah** dengan CSS dan JavaScript bersama. Tidak memakai client router, framework, atau build Node.js.

| Halaman | File | Isi utama |
|---|---|---|
| **Market Overview** | `index.html` | target tabs, Data Provenance Bar, ringkasan skor, grafik harga/return vs sentimen, berita teratas |
| **News & Evidence** | `evidence.html` | filter berita, evidence cards, Evidence Drawer, tone vs direction, waktu publikasi vs sesi efektif |
| **Research Lab** | `research.html` | Association Workbench, statistik, confusion matrix, ECE/reliability, Data Quality Panel |
| **Simulations** | `simulations.html` | Allocation Tilt, baseline profil, Persona POV, parameter/version, disclaimer |

Struktur file minimum:

```text
frontend/GUI/
├── index.html
├── evidence.html
├── research.html
├── simulations.html
├── src/css/
│   ├── theme.css
│   ├── layout.css
│   └── splash.css
└── src/js/
    ├── api.js
    ├── state.js
    ├── shell.js
    ├── splash.js
    └── pages/
        ├── overview.js
        ├── evidence.js
        ├── research.js
        └── simulations.js
```

Tanggung jawab modul:

- `api.js`: deteksi base URL, fetch, mode live/snapshot/demo, error normalizer;
- `state.js`: target/range/profile melalui `URLSearchParams`, agar state bertahan antarhalaman;
- `shell.js`: navigasi bersama, disclaimer, status API, target context, helper format/escape;
- `pages/*.js`: hanya fetch dan render khusus halaman;
- `theme.css`: token global; `layout.css`: shell dan komponen bersama; CSS spesifik halaman hanya bila benar-benar perlu.

Aturan navigasi:

- tautan biasa ke empat file; tanpa hash-router;
- query dibawa saat pindah halaman, misalnya `research.html?target=XAU&days=90`;
- hotkey `1–4` hanya saat fokus tidak berada pada input;
- setiap halaman tetap menampilkan mode data dan disclaimer;
- mobile memakai nav horizontal atau menu ringkas.

### 3.1 Adaptasi Splash Screen yang Sudah Ada

Basis tersedia di `frontend/splash-screen/`:

- `splash.js`: mode `full`, `quick`, `skeleton`, `none`, session gate, `Splash.done()`;
- `splash.css`: overlay dan progress bar;
- `index-example.html`: contoh pemasangan;
- `tokens.css`: referensi visual saja;
- `config.toml`: khusus Streamlit, **jangan dipakai**.

Integrasi yang direkomendasikan:

1. Pindahkan/adaptasi `splash.js` dan `splash.css` ke `frontend/GUI/src/`; jangan duplikasi per halaman.
2. Pakai token/font lokal dari `frontend/GUI/src/css/theme.css`; jangan salin `tokens.css` mentah karena masih memakai Google Fonts CDN.
3. Konfigurasi pertama dalam sesi: `full`; navigasi/reload berikutnya: `skeleton` atau `none`.
4. Set `waitForApp: true`; panggil `Splash.done()` setelah `/health`, `/api/meta`, dan `/api/universe` selesai atau fallback dipilih.
5. Ganti log timer palsu dengan status nyata: `CHECKING API`, `LOADING METADATA`, `LOADING UNIVERSE`, lalu `LIVE`, `SNAPSHOT`, atau `DEMO`.
6. Kurangi durasi contoh (`fullMs: 2600`) menjadi maksimal sekitar 900 ms untuk minimum visual; `maxMs` tetap menjadi pengaman, bukan waktu tunggu normal.
7. Splash penuh hanya di `index.html` pada kunjungan pertama. Halaman lain memakai progress bar skeleton agar navigasi tidak terasa diulang.
8. Pertahankan `prefers-reduced-motion`, `role="status"`, dan event `splash:done`.

Isi splash:

- identitas `ARCAS : Sentiment Desk`;
- status API/database;
- mode `live`, `snapshot`, atau `demo`;
- versi model/universe/schema;
- tiga target inti yang berhasil dimuat.

Tanpa video, audio, WebGL, slogan berganti, atau progress yang mengklaim model sudah dimuat sebelum respons nyata. Splash baru diintegrasikan setelah UI-01 dan `/api/meta` tersedia; sebelumnya status badge aktif tetap dipakai.

## 4. Prioritas Upgrade

### P0 — Wajib sebelum UI disebut siap riset

#### UI-01 — Data Provenance Bar

Tampilkan metadata berikut dekat status API:

- mode data: `live`, `snapshot`, atau `demo`;
- `updated_at` dan rentang data;
- `model_version`, `universe_version`, `schema_version`, `params_version` bila relevan;
- jumlah artikel, sumber, dan hari yang tercakup;
- status model: `calibrated` atau `uncalibrated`.

**Lokasi:** `frontend/GUI/src/js/api.js`, `state.js`, `shell.js`, layout bersama, dan endpoint metadata ringkas di `backend/src/serve/app.py`.

**Selesai bila:** pengguna selalu dapat membedakan data nyata dari ilustrasi dan mengetahui versi yang menghasilkan hasil.

#### UI-02 — Audit Waktu dan Lag

Pada kartu berita dan panel statistik tampilkan:

- `published_at` beserta timezone;
- `effective_trading_date`;
- cut-off/sesi pasar target;
- lag yang diuji;
- periode dan jumlah observasi.

Berita setelah sesi tutup harus terlihat masuk ke sesi berikutnya. Istilah UI: **“diasosiasikan pada lag N”**, bukan “menyebabkan”.

**Lokasi:** join artikel–impact di storage/API, `frontend/GUI/src/js/pages/evidence.js`, `frontend/TUI/` saat implementasi TUI dimulai.

**Selesai bila:** satu berita dapat ditelusuri dari waktu terbit ke bucket pasar yang dipakai analisis.

#### UI-03 — Provenance dan Evidence Drawer

Kartu dampak diperluas dengan detail yang dapat dibuka:

- headline, sumber, URL, bahasa, dan target;
- kutipan persis;
- `tone` dipisahkan dari `direction`;
- `basis`, tema, causal path, flags, rationale;
- probabilitas tiga kelas dan nama/versi model;
- badge `Headline only` bila body tidak dianalisis.

**Lokasi:** kontrak response impact detail, `backend/src/serve/app.py`, `frontend/GUI/evidence.html`, dan `src/js/pages/evidence.js`.

**Selesai bila:** setiap skor di UI dapat dilacak ke input dan modelnya tanpa membuka database.

#### UI-04 — Model Quality & Calibration

Tambahkan panel evaluasi, bukan gauge confidence tunggal:

- F1 macro, precision/recall per kelas, Cohen's kappa;
- confusion matrix 3×3;
- ECE dan reliability diagram;
- histogram jumlah sampel per confidence bin;
- model, dataset, periode evaluasi, dan ukuran sampel.

Temperature scaling harus dijelaskan sebagai koreksi confidence, bukan peningkatan akurasi.

**Lokasi:** artefak `model/evaluation/`, endpoint evaluasi read-only, `frontend/GUI/research.html`, dan `src/js/pages/research.js`.

**Selesai bila:** confidence per berita tidak dapat disalahartikan sebagai probabilitas pasar naik.

### P1 — Nilai analitis tinggi

#### UI-05 — Association Workbench

Upgrade grafik/tabel asosiasi dengan kontrol minimum:

- market metric: return, perubahan yield, volatilitas, volume;
- lag dan rolling window;
- estimate, confidence interval, `p_value`, `p_adjusted`, `n_obs`;
- penanda event window untuk CAR;
- volume berita dan jumlah hari kosong.

Default asosiasi memakai **return/perubahan yield**, bukan kemiripan level harga. Level harga boleh tetap menjadi konteks visual sekunder.

**Lokasi:** `backend/src/stats/`, `backend/src/serve/app.py`, `frontend/GUI/research.html`, dan `src/js/pages/research.js`.

**Selesai bila:** pengguna dapat melihat bahwa arah/ukuran hubungan dapat berubah menurut lag, window, dan rezim.

#### UI-06 — Data Quality Panel

Tampilkan:

- jumlah artikel per sumber/kelas/target;
- hari tanpa berita sebagai gap;
- duplikasi/penolakan validator;
- nilai observasi versus nilai turunan/imputasi bila kelak dipakai;
- kelengkapan headline/body/evidence;
- warning kelas langka dan cakupan instrumen yang belum tervalidasi langsung.

**Lokasi:** agregasi quality metadata backend, panel ringkas GUI/TUI.

**Selesai bila:** rata-rata sentimen selalu memiliki denominator dan status kelengkapan.

### P2 — Setelah P0/P1 stabil

- ekspor CSV/JSON untuk tampilan aktif;
- snapshot HTML memakai tema dan payload yang sama dengan GUI aktif;
- perbandingan tiga target dalam small multiples;
- log alert sentimen ekstrem yang menampilkan precision/recall dan false-alarm rate.

## 5. Perubahan Kontrak Minimum

Hindari endpoint per-widget. Tambahkan dua kontrak ringkas:

1. `GET /api/meta` — freshness, mode data, versi, cakupan, status kalibrasi.
2. `GET /api/evaluation/{model}` — metrik evaluasi dan calibration bins.

Perluas response impact dengan metadata artikel melalui join; jangan membuat endpoint baru bila `/api/impacts/{target}` masih dapat tetap ringan.

Perubahan model Pydantic atau persistence wajib mengikuti aturan `SCHEMA.md`: bump versi bila struktur kontrak berubah.

## 6. Urutan Implementasi

1. UI-01 Data Provenance Bar + `/api/meta`.
2. Shell empat view + Boot/Preflight Screen.
3. UI-02 Audit Waktu dan Lag.
4. UI-03 Provenance/Evidence Drawer.
5. UI-04 Model Quality & Calibration.
6. UI-05 Association Workbench.
7. UI-06 Data Quality Panel.
8. P2 hanya setelah acceptance P0/P1 lolos.

## 7. Yang Sengaja Tidak Dibuat

- tidak ada prediksi harga atau badge “peluang naik”;
- tidak ada chatbot, LLM, RAG, atau agent;
- tidak ada heatmap dekoratif tanpa denominator;
- tidak ada framework frontend baru, Node.js, Streamlit, atau CDN;
- tidak ada ekspansi universe di luar `XAU`, `RATE_UST`, `SPX`;
- tidak ada personalization yang menyebut “sesuai profil Anda”.

## 8. Acceptance Global

- Disclaimer **“Asosiasi historis — nonkausal, nonprediktif. Bukan nasihat investasi.”** terlihat pada tiap layar utama.
- Demo/snapshot/live tidak pernah terlihat sama tanpa label.
- Warna bukan satu-satunya pembawa makna.
- Hari tanpa berita tetap `NaN`/gap.
- Semua angka statistik menampilkan periode dan `n_obs`.
- Semua skor berita dapat ditelusuri ke evidence, model, dan versi.
- GUI tetap Vanilla HTML/CSS/JS + ECharts offline; backend tetap FastAPI; RAM target tetap <50 MB.

## 9. Dasar Riset Ringkas

- Kalibrasi confidence dan reliability diagram: `papers_calibration_ece_guo2017.pdf`.
- Alignment sesi, lag, return, dan anti-lookahead: `papers_stfa_semantictime.pdf`, `papers_finbert_lstm.pdf`.
- Provenance dan batas generalisasi model: `papers_finbert_original_araci2019.pdf`, `papers_fnspid_dataset.pdf`.
- Granger/event study harus menampilkan lag, window, n, dan bahasa nonkausal: `papers_granger_news_return.pdf`, `papers_twitter_djia_eventstudy.pdf`.
- Agregat perlu denominator, kelas, dan konteks multi-label: `papers_phrasebank_malo2014.pdf`, `papers_gold_commodity_news_sinha2020.pdf`.
- Rolling association dan dispersi dapat berubah menurut periode: `papers_finbert_famafrench.pdf`.

> Catatan integritas katalog: `research/papers/papers_indobert_indolem.pdf` tidak berisi paper IndoBERT/IndoLEM sebagaimana namanya. Ganti sumber sebelum menjadikannya dasar klaim.
