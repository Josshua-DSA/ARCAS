# frontend/GUI/ — Static ECharts HTML Dashboard (FR-15)

Dashboard web statis offline (zero-build, zero-server) untuk artefak presentasi sidang:
- `src/css/`: Styling ikut `THEME.md` v0.1 (Claude × Bloomberg, offline adaptasi): font Newsreader/Inter/JetBrains Mono via `@font-face` lokal `src/fonts/`, Base `#F6F4F4`, Surface `#FFFFFF`, Technical `#3E3939`, Accent `#FF7517`, Text `#2C2727`, semantik UP/DOWN/HOLD + palet grafik; proporsi 65/20/10/5, filosofi 70% Claude + 30% Bloomberg. `layout.css` berisi shell bersama; CSS spesifik halaman tidak diperlukan, semua halaman memakai set yang sama.
- `src/js/api.js`: layer API tanpa build (deteksi base relatif lalu localhost, fetch, penyedia data ilustrasi berlabel `demoSeries`/`demoImpacts`/`demoQuality`).
- `src/js/state.js`: state antarhalaman lewat `URLSearchParams` (`?target=XAU&days=90&profile=moderate`), tautan dan reload selalu membawa state.
- `src/js/shell.js`: shell bersama: helper format/escape, status API, Provenance Bar, tab target (dari `/api/universe`), tabel statistik, widget alokasi, modal Persona, navigasi 4 halaman dengan hotkey `1-4` (target pakai tombol arah di tab fokus), dan boot yang menutup splash hanya setelah data nyata.
- `src/js/pages/*.js`: satu file per halaman, hanya fetch dan render: `overview.js` (index), `evidence.js`, `research.js`, `simulations.js`.
- `templates/`: Template HTML single-file yang di-inject JSON payload dari backend CLI `report`.
- **HTML**: `index.html` (Market Overview: grafik, statistik ringkas, strip alokasi, berita teratas), `evidence.html` (arus berita, kutipan, audit waktu, drawer, persona), `research.html` (statistik lengkap, meja kerja asosiasi, kualitas data, panel kualitas model), `simulations.html` (allocation tilt per profil, Persona POV, parameter/versi). Navigasi: tautan biasa membawa query, tanpa hash-router, tanpa build.
- **Fitur**: Dual-axis sentimen vs harga, tab 3 target inti (label pemula `Emas`, `Suku Bunga`, `S&P 500`; ID `XAU`, `RATE_UST`, `SPX` tetap dipakai di API), dirender dinamis dari `/api/universe`.
- **Splash + provenance (Upgrade.md UI-01)**: `src/js/splash.js` menampilkan splash penuh pada setiap refresh dan navigasi antarhalaman, dengan log boot beranimasi (baris masuk berurutan, tandai `OK`, timestamp nyata) dan bar progres bergerak. `Splash.done()` setelah `/api/meta` + `/api/universe` selesai atau fallback dipilih, jadi tidak ada timer palsu. `src/css/splash.css` memakai token `theme.css`, bukan `tokens.css` komponen (yang masih CDN). Data Provenance Bar menampilkan mode `live`/`demo`, versi universe/skema/model, cakupan artikel & hari berita.
- **Audit waktu (Upgrade.md UI-02)**: tiap kartu dampak memuat baris audit `terbit vs sesi efektif vs cut-off` (join `articles` + `article_targets` + `asset_master` di `/api/impacts`), berita setelah cut-off bertanda "masuk sesi berikutnya". Panel statistik menampilkan periode uji dan lag yang diuji.
- **Evidence drawer (Upgrade.md UI-03)**: tiap kartu punya `<details>` "Bukti dan model" berisi probabilitas tiga kelas per model (`p_pos/p_neu/p_neg` dari tabel `sentiments`), badge "Hanya judul yang dianalisis", dan tautan sumber asli. Bagian yang belum terekam di DB selalu disebut jujur, tidak pernah dipalsukan.
- **Ikon aset target**: tab memakai line icon SVG lokal di `src/assets/` (lingot emas, tanda persen, garis tren memutar), warna tunggal tinta `#2C2727`, ukuran 28px, tanpa CDN dan tanpa logo berhak cipta; Ikon S&P 500 adalah stilisasi generik, bukan logo resmi.
- **Panel kualitas data (Upgrade.md UI-06, mockup)**: panel "Kualitas data" saat ini memakai data mock hard-coded yang **berlabel MOCKUP** di dalam panel. Bentuk datanya mengikuti kontrak `/api/quality` yang dirancang, jadi saat backend menyediakan endpoint, `loadQuality()` tinggal ditukar ke pemanggilan API tanpa mengubah renderer. Backend sengaja tidak disentuh (disiplin frontend).
- **Meja kerja asosiasi (Upgrade.md UI-05, di Research Lab)**: kontrol metrik pasar (opsi dibangun dari data, bukan daftar karangan) dan tombol "Hitung Spearman L0..L5" yang menghitung ulang Spearman live via `/api/stats/{target}?max_lag=5`, lengkap 95% CI saat tersedia, penurunan `n_obs` per lag, dan penanda jendela CAR dari `params_json`. Pembaca bisa melihat sendiri bahwa arah/ukuran hubungan berubah menurut lag. Catatan kejujuran: angka L0 mencapai 1.000 karena seed demo bersifat sintetis berpola alternasi, bukan sinyal pasar nyata. Rolling window belum ada di engine, jadi kontrolnya tidak dipalsukan di UI.
- **Output**: File beku `outputs/report.html` (dapat dibuka langsung di browser).

## Tampilan Dashboard (`docs/tampilan-dashboard/`)

Hasil tangkapan layar dari data demo (API lokal + `data/finews.db` terisi):

![Ringkasan + grafik harga vs sentimen](../../docs/tampilan-dashboard/01-ringkas-grafik.png)
![Alokasi tilt + berita berdampak](../../docs/tampilan-dashboard/02-alokasi-berita.png)
![Modal Persona POV](../../docs/tampilan-dashboard/03-persona-pov.png)
![Tampilan mobile 390px](../../docs/tampilan-dashboard/04-mobile.png)
![Splash boot dengan status nyata](../../docs/tampilan-dashboard/06-splash-boot.png)
![Mode demo berlabel saat API mati](../../docs/tampilan-dashboard/05-mode-demo.png)
