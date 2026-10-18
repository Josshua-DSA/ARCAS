# Theme & Splash — Bloomberg 70% × Claude 30%

| File | Fungsi |
|---|---|
| `tokens.css` | Warna, font, komponen (panel, paper card, tape, chip, tabel, skeleton) |
| `splash.css` + `splash.js` | Splash/preloader: penuh (kunjungan pertama), singkat/skeleton/none (reload) |
| `index.example.html` | Contoh pemasangan 4 langkah |
| `streamlit_theme.py` + `.streamlit/config.toml` | Versi Streamlit (tema + splash CSS-only) |

## Web biasa
1. Salin `tokens.css`, `splash.css`, `splash.js`; pasang seperti di `index.example.html`.
2. Atur `window.SPLASH_CONFIG` (`reloadMode`, durasi, `waitForApp`).
3. Bila menunggu data: `waitForApp: true`, lalu panggil `Splash.done()` setelah data siap.
4. Event `splash:done` dikirim ke `document` (berisi mode dan durasi).

## Streamlit
1. Salin `streamlit_theme.py` dan `.streamlit/config.toml` ke root proyek.
2. Di `app.py`: `apply_theme()` lalu `splash_once()`.

## Catatan
- Kontras seluruh token teks sudah diverifikasi (lihat `GUI_THEME_70B.md`).
- Teks di atas oranye/amber harus gelap (`--on-accent`).
- Animasi otomatis mati bila pengguna memakai `prefers-reduced-motion`.
- Disclaimer "Bukan nasihat investasi" tetap wajib di tampilan yang memuat chip BUY/SELL.
