# frontend/GUI/ — Static ECharts HTML Dashboard (FR-15)

Dashboard web statis offline (zero-build, zero-server) untuk artefak presentasi sidang:
- `src/css/`: Styling ikut `THEME.md` v0.1 (Claude × Bloomberg, offline adaptasi): font Newsreader/Inter/JetBrains Mono via `@font-face` lokal `src/fonts/`, Base `#F6F4F4`, Surface `#FFFFFF`, Technical `#3E3939`, Accent `#FF7517`, Text `#2C2727`, semantik UP/DOWN/HOLD + palet grafik; proporsi 65/20/10/5, filosofi 70% Claude + 30% Bloomberg.
- `src/js/`: Inisialisasi Apache ECharts offline (vendored, zero-CDN).
- `templates/`: Template HTML single-file yang di-inject JSON payload dari backend CLI `report`.
- **Fitur**: Dual-axis sentimen vs harga, tab 3 target inti (`XAU`, `RATE_UST`, `SPX`, dirender dinamis dari `/api/universe`), evidence table, statistik, kartu Allocation Tilt & Persona POV.
- **Output**: File beku `outputs/report.html` (dapat dibuka langsung di browser).

## Tampilan Dashboard (`docs/tampilan-dashboard/`)

Hasil tangkapan layar dari data demo (API lokal + `data/finews.db` terisi):

![Ringkasan + grafik harga vs sentimen](../../docs/tampilan-dashboard/01-ringkas-grafik.png)
![Alokasi tilt + berita berdampak](../../docs/tampilan-dashboard/02-alokasi-berita.png)
![Modal Persona POV](../../docs/tampilan-dashboard/03-persona-pov.png)
![Tampilan mobile 390px](../../docs/tampilan-dashboard/04-mobile.png)
