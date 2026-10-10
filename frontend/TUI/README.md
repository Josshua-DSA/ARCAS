# frontend/TUI/ — Terminal User Interface (Bloomberg-style)

TUI interaktif berbasis Python Rich & Textual untuk inspeksi quant trading & sentimen:
- **Desain**: Tema Dark Financial kustom (Base `#2C2727`, Surface `#3E3939`, Accent `#FF7517`, Text `#F6F4F4`).
- **Interaksi**: Keyboard-driven murni (hotkeys angka `1-5` tab, panah navigasi, `/` filter, `q` quit).
- **Tampilan**:
  - Panel deret waktu ASCII/sparkline per target.
  - Tabel bukti berita (`TargetImpact`) dengan badge sentimen & confidence.
  - Ringkasan statistik (Spearman, OLS HAC, Granger, CAR).
  - Alokasi dinamis (Allocation Tilt) & kartu Persona POV.
- **Konsumsi**: Membaca database SQLite (`TargetImpact`, `DailySentiment`, `PriceRecord`) atau payload JSON backend.
