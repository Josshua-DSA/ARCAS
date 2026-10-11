# frontend/ — Lapisan Presentasi

Direktori antarmuka pengguna dibagi menjadi dua:

1. **`GUI/` (Web Statis Offline — FR-15)**:
   - Single-file HTML beku + Apache ECharts offline (zero-CDN).
   - Di-generate via CLI backend (`outputs/report.html`).
   - Aman untuk sidang: bebas crash, tanpa runtime Node.js/Python aktif saat demo.

2. **`TUI/` (Terminal Interaktif — Bloomberg Style)**:
   - Berbasis Python Rich / Textual.
   - Tema Dark Financial (Base `#2C2727`, Surface `#3E3939`, Accent `#FF7517`, Text `#F6F4F4`), navigasi keyboard-driven murni.
   - Live browser di terminal untuk inspeksi kuantitatif, log berita, sentimen harian, dan simulasi alokasi.
