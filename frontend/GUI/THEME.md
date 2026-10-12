# GUI THEME — Claude × Bloomberg

> Versi: v0.1 · Terkait: `DESIGN.md` §8 (Antarmuka), `RULES.md` §11 (aturan tampilan BUY/SELL)
> Semua angka kontras dihitung dengan rumus WCAG 2.x (relative luminance). Teks kecil ≥ 4,5:1, teks besar (≥ 18px atau ≥ 14px tebal) dan komponen grafis ≥ 3:1.

## 1. Konsep

Tema ini membagi tampilan menjadi dua lapisan.

| Lapisan | Latar | Isi | Karakter |
|---|---|---|---|
| **Narasi** | Base terang `#F6F4F4` | Judul berita, ringkasan, rationale, navigasi, hero | Claude: kertas hangat, serif editorial |
| **Data** | Technical Surface gelap `#3E3939` | Tabel, ticker, grafik, panel statistik, kode, footer | Bloomberg: terminal padat, mono, angka rapat |
| **Aksen** | Oranye `#FF7517` | CTA, tab aktif, garis dekoratif, angka unggulan | Penyatu kedua lapisan |

**Aturan inti:** teks yang dibaca di lapisan terang dengan serif; angka dan data di lapisan gelap dengan mono.

## 2. Warna Inti (dari spesifikasi)

| Token | Hex | Peran |
|---|---|---|
| `--base` | `#F6F4F4` | Background halaman, hero, area konten |
| `--text` | `#2C2727` | Heading, paragraf, navbar, ikon utama, teks tombol aksen |
| `--accent` | `#FF7517` | CTA, link aktif, garis dekoratif, indikator tab aktif, angka statistik unggulan, 1–2 card pilihan |
| `--surface` | `#3E3939` | Panel terminal, code block, panel statistik gelap, metadata teknis, footer |

## 3. Token Turunan — Sisi Terang

| Token | Hex | Dipakai untuk | Kontras |
|---|---|---|---|
| `--bg-card` | `#FFFFFF` | Card terangkat di atas base | — |
| `--bg-sunken` | `#EDEAEA` | Area cekung, hover baris, input | — |
| `--text-primary` | `#2C2727` | Teks utama | 13,4:1 di base |
| `--text-secondary` | `#5E5757` | Teks pendukung, caption | 6,4:1 di base |
| `--text-muted` | `#6B6464` | Placeholder, metadata | 5,3:1 di base; 4,8:1 di sunken |
| `--border-subtle` | `#DDD8D8` | Garis pemisah dekoratif (bukan batas kontrol) | 1,3:1 |
| `--border-strong` | `#8C8585` | Batas input, tombol sekunder, kontrol | 3,3:1 di base |
| `--accent` | `#FF7517` | **Fill, garis, border, tab aktif** (bukan teks kecil) | 2,5:1 di base |
| `--accent-hover` | `#FF8A3D` | Hover tombol aksen (lebih terang) | teks gelap di atasnya 6,3:1 |
| `--accent-text` | `#C2410C` | **Teks/link beraksen di latar terang** | 4,7:1 di base; 5,2:1 di card |
| `--accent-subtle` | `#FFE9DB` | Latar tint (baris terpilih, callout); isi dengan teks `--text-primary` | — |

## 4. Token Turunan — Sisi Gelap (Technical Surface)

| Token | Hex | Dipakai untuk | Kontras |
|---|---|---|---|
| `--surface-deep` | `#2C2727` | Latar bersarang terdalam (footer, kode di dalam panel) | — |
| `--surface` | `#3E3939` | Panel utama | — |
| `--surface-raised` | `#4A4545` | Hover baris, card di dalam panel | — |
| `--on-dark-primary` | `#F6F4F4` | Teks utama di panel | 10,4:1 di surface; 8,6:1 di raised |
| `--on-dark-secondary` | `#D4CFCF` | Teks pendukung | 7,4:1 / 6,1:1 |
| `--on-dark-muted` | `#BDB7B7` | Metadata, label kolom | 5,7:1 / 4,8:1 |
| `--border-dark-subtle` | `#5A5454` | Garis tabel | 1,5:1 (dekoratif) |
| `--border-dark-strong` | `#8C8585` | Batas kontrol di panel gelap | 3,1:1 |
| `--accent-on-dark` | `#FF7517` | Angka besar, garis, indikator | 4,2:1 di surface; 5,5:1 di deep |
| `--accent-text-on-dark` | `#FF8A3D` | **Teks kecil beraksen di panel gelap** | 4,8:1 di surface |

Catatan: `#A8A2A2` hanya 3,8:1 di `surface-raised`, jangan dipakai sebagai teks di sana.

## 5. Aturan Penggunaan Aksen

1. Tombol primer: latar `--accent`, **teks `--text` (gelap)**. Teks putih di atas oranye hanya 2,7:1 sehingga dilarang.
2. Link dan teks beraksen di latar terang: `--accent-text` (`#C2410C`), bukan `--accent`. Jangan di `--bg-sunken` untuk teks kecil (4,3:1).
3. Di panel gelap: oranye penuh untuk angka besar dan garis; teks kecil beraksen pakai `--accent-text-on-dark`.
4. Oranye **tidak boleh** dipakai untuk arah data (naik/turun/jual). Itu tugas warna semantik (bagian 6).
5. Batasi: satu aksen oranye dominan per layar, plus maksimal 1–2 card pilihan.
6. Hover tombol aksen: `--accent-hover`. Pressed: `--accent` ditambah `transform: translateY(1px)`.

## 6. Warna Semantik (data)

| Makna | Latar terang (teks/ikon) | Panel gelap (teks/ikon) |
|---|---|---|
| Naik / Bullish / BUY | `#1A7F37` (4,6:1) | `#56D364` (5,9:1 di surface) |
| Turun / Bearish / SELL | `#CF222E` (4,9:1) | `#FF7B72` (4,5:1 di surface; 5,8:1 di deep) |
| Netral / HOLD | `#6B6464` (5,3:1) | `#BDB7B7` (5,7:1) |
| Peringatan / Mixed | `#8A5A00` (5,4:1) | `#FFB000` (6,2:1) |
| Info | `#0969DA` (4,7:1) | `#79B8FF` (5,5:1) |

Aturan:
- Warna **tidak boleh** satu-satunya pembawa makna: selalu sertakan **ikon/simbol dan tanda**, mis. `▲ +0.42`, `▼ −0.31`, `● 0.00`, `BUY`/`SELL`/`HOLD`.
- `#FF7B72` hanya untuk teks di `surface` atau `surface-deep`. Di `surface-raised` (3,7:1) hanya untuk teks besar/tebal.
- Di atas latar tint (hijau/merah muda), isi teks pakai `--text-primary`; warna semantik hanya sebagai garis kiri atau ikon.

### Chip Persona POV (diisi penuh, berlaku di tema terang dan gelap)

| Chip | Latar | Teks | Kontras teks |
|---|---|---|---|
| BUY | `#1A7F37` | `#FFFFFF` | 5,1:1 |
| SELL | `#CF222E` | `#FFFFFF` | 5,4:1 |
| HOLD | `#6B6464` | `#FFFFFF` | 5,8:1 |

Kekuatan stance (`strength`) ditunjukkan dengan **bar kecil atau titik 1–5** di samping chip, bukan dengan mengubah opasitas warna (opasitas rendah merusak kontras). Wajib tampilkan label **"Simulasi sudut pandang. Bukan nasihat investasi."** di komponen yang sama.

## 7. Skala Sentimen (heatmap / sel tabel)

Skala divergen 5 langkah untuk skor −1 … +1. Tampilkan angka dan tanda di dalam sel.

| Skor | Panel gelap | Latar terang |
|---|---|---|
| −1,0 | `#FF7B72` | `#CF222E` |
| −0,5 | `#AC6863` | `#DE868C` |
| 0 | `#5A5454` | `#EDEAEA` |
| +0,5 | `#58945C` | `#84B490` |
| +1,0 | `#56D364` | `#1A7F37` |

Teks di dalam sel diuji per kombinasi (teks `--on-dark-primary` di sel gelap, `--text-primary` di sel terang). Langkah tengah (±0,5) belum diuji kontrasnya per sel; periksa saat implementasi.

## 8. Palet Grafik

Grafik diutamakan di panel gelap. Syarat komponen grafis ≥ 3:1 terpenuhi untuk semua seri berikut.

| Seri | Panel gelap | Kontras di surface | Latar terang | Kontras di base |
|---|---|---|---|---|
| Emas (XAU) | `#FFD33D` | 7,9:1 | `#9A6700` | 4,4:1 |
| Yield UST (RATE_UST) | `#58A6FF` | 4,5:1 | `#0969DA` | 4,7:1 |
| S&P 500 (SPX) | `#FF7517` | 4,2:1 | `#C2410C` | 4,7:1 |
| Netral A | `#2FC4B2` | 5,2:1 | `#1F9D8A` | 3,1:1 |
| Netral B | `#D2A8FF` | 5,8:1 | `#8B5CF6` | 3,9:1 |

Aturan grafik:
- Warna seri **bukan** warna arah. Untuk naik/turun (candlestick, bar perubahan) pakai warna semantik bagian 6.
- Seri Perbankan mirip hijau "naik"; jangan tampilkan keduanya dalam satu grafik tanpa pembeda (garis putus-putus/marker).
- Lebih dari 5 seri dalam satu grafik: bedakan juga dengan gaya garis atau marker.
- Garis grid: `#5A5454` (gelap) / `#DDD8D8` (terang), tipis dan redup. Teks sumbu: `--on-dark-muted` / `--text-muted`.

## 9. State Interaksi

| State | Terang | Gelap |
|---|---|---|
| Hover baris | `--bg-sunken` | `--surface-raised` |
| Baris/tab terpilih | latar `--accent-subtle` + garis kiri 3px `--accent` | latar `rgba(255,117,23,0.16)` + garis kiri 3px `--accent` |
| Fokus keyboard | outline 2px `#2C2727`, offset 2px, ditambah ring `0 0 0 4px #FF7517` | outline 2px `#F6F4F4`, offset 2px, ditambah ring `0 0 0 4px #FF7517` |
| Disabled | opasitas 0,5, tanpa hover | opasitas 0,5, tanpa hover |
| Error input | border `#CF222E` + ikon + teks pesan | border `#FF7B72` + ikon + teks pesan |

Cincin fokus memakai warna gelap/terang sebagai garis utama karena oranye saja hanya 2,5:1 di base.

## 10. Tipografi (ringkas; versi font gratis padanan)

| Peran | Font | Dipakai untuk |
|---|---|---|
| Narasi / heading | Newsreader 300–400 (alt: Source Serif 4, Lora) | Judul halaman, judul berita, ringkasan, rationale |
| UI | Inter 400/500/600 (alt: IBM Plex Sans) | Menu, tombol, label, tab |
| Data | JetBrains Mono 400/500 (alt: IBM Plex Mono) | Harga, skor, confidence, ticker, tabel, chip |

- Angka: `font-variant-numeric: tabular-nums`.
- Label kecil dan chip: mono, kapital, `letter-spacing: 0.06em`, 11–12px.
- Font asli Claude (Anthropic Sans/Serif) dan Bloomberg bersifat proprietary dan tidak dipakai.

## 11. CSS Variables (siap salin)

```css
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,300;6..72,400&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  /* inti */
  --base: #F6F4F4;  --text: #2C2727;  --accent: #FF7517;  --surface: #3E3939;

  /* terang */
  --bg-card: #FFFFFF;  --bg-sunken: #EDEAEA;
  --text-primary: #2C2727;  --text-secondary: #5E5757;  --text-muted: #6B6464;
  --border-subtle: #DDD8D8;  --border-strong: #8C8585;
  --accent-hover: #FF8A3D;  --accent-text: #C2410C;  --accent-subtle: #FFE9DB;

  /* gelap */
  --surface-deep: #2C2727;  --surface-raised: #4A4545;
  --on-dark-primary: #F6F4F4;  --on-dark-secondary: #D4CFCF;  --on-dark-muted: #BDB7B7;
  --border-dark-subtle: #5A5454;  --border-dark-strong: #8C8585;
  --accent-text-on-dark: #FF8A3D;

  /* semantik: terang */
  --up: #1A7F37;  --down: #CF222E;  --hold: #6B6464;  --warn: #8A5A00;  --info: #0969DA;
  /* semantik: gelap */
  --up-dark: #56D364;  --down-dark: #FF7B72;  --hold-dark: #BDB7B7;  --warn-dark: #FFB000;  --info-dark: #79B8FF;

  /* font */
  --font-serif: "Newsreader", Georgia, serif;
  --font-sans: "Inter", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
}

body { background: var(--base); color: var(--text-primary); font-family: var(--font-sans); }
h1, h2, .news-title, .rationale { font-family: var(--font-serif); font-weight: 350; }
.panel-dark { background: var(--surface); color: var(--on-dark-primary); }
.num, .ticker, .panel-dark td { font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.btn-primary { background: var(--accent); color: var(--text); }
.btn-primary:hover { background: var(--accent-hover); }
a { color: var(--accent-text); }
.chip { font-family: var(--font-mono); font-size: 11px; letter-spacing: .06em; text-transform: uppercase; color: #fff; }
.chip.buy { background: var(--up); } .chip.sell { background: var(--down); } .chip.hold { background: var(--hold); }
:focus-visible { outline: 2px solid var(--text); outline-offset: 2px; box-shadow: 0 0 0 4px var(--accent); }
```

## 12. Konfigurasi Streamlit (jika dipakai; cek dukungan font kustom pada versi yang dipakai)

```toml
# .streamlit/config.toml
[theme]
primaryColor = "#FF7517"
backgroundColor = "#F6F4F4"
secondaryBackgroundColor = "#EDEAEA"
textColor = "#2C2727"
font = "sans serif"
```
Panel gelap, font kustom, dan chip memakai CSS yang disuntikkan lewat `st.markdown(..., unsafe_allow_html=True)`.

## 13. Daftar Periksa Implementasi

- [ ] Tidak ada teks putih di atas `--accent`.
- [ ] Teks kecil beraksen memakai `--accent-text` (terang) atau `--accent-text-on-dark` (gelap).
- [ ] Setiap warna semantik disertai ikon/tanda dan teks.
- [ ] Chip BUY/SELL/HOLD diberi label "Simulasi sudut pandang".
- [ ] Grafik dengan > 5 seri memakai gaya garis berbeda.
- [ ] Fokus keyboard terlihat di semua kontrol.
- [ ] Uji ulang kontras sel heatmap langkah ±0,5.