# Evaluasi Model ARCAS

Digenerate: 2026-11-04 · oleh `scripts/evaluasi_model.py`

Semua angka di bawah dibaca dari artefak evaluasi yang tersimpan di disk. Tidak ada yang dihitung ulang saat laporan dibuat, supaya angka di dokumen ini tidak bisa berbeda dari angka yang dipakai model.

Evaluasi ini mengukur **kualitas model membaca teks**, bukan profit trading. Sesuai `context/RULES.md` §11.9, fitur tidak dinilai dari untung-rugi.

---

## Emas (FinBERT-EMAS)
- Model: `xau-finbert-20261025`
- Basis: `yiyanghkust/finbert-tone`
- Pembagian data: latih 5849, validasi 1033, uji 1720
- Seed: 5768 · epoch 3 · lr 2e-05 · batch 16

### Ringkasan pada set uji

| Metrik | Nilai |
|---|---|
| Sampel uji | 1720 |
| Akurasi | 0.9517 |
| Macro F1 | 0.8887 |
| ECE sebelum kalibrasi | 0.0176 |
| ECE sesudah kalibrasi | 0.0074 |
| Ambang ECE | 0.1000 |

Kalibrasi suhu menurunkan ECE 58%, dari 0.0176 ke 0.0074.

### Per kelas

| Kelas | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| negative | 0.9485 | 0.9634 | 0.9558 | 764 |
| neutral | 0.9583 | 0.6133 | 0.7480 | 75 |
| positive | 0.9542 | 0.9705 | 0.9623 | 881 |

### Matriks konfusi

Baris = aktual, kolom = prediksi.

| aktual \ prediksi | negative | neutral | positive |
|---|---|---|---|
| **negative** | 736 | 0 | 28 |
| **neutral** | 16 | 46 | 13 |
| **positive** | 24 | 2 | 855 |

## FOMC (RoBERTa)

**Metrik tidak tersedia.** `model/fomc/weights/metrics.json` belum ada: bobot hasil pelatihan tidak ikut ter-clone (`.gitignore`), dan skrip evaluasi FOMC belum menulis ringkasan metrik.

Untuk melengkapinya: jalankan `python scripts/fetch_weights.py` lalu `model/fomc/evaluation/evaluate_holdout.py`, dan simpan hasilnya ke `model/fomc/weights/metrics.json`.

---

## Router: pemilihan model spesialis

Diukur langsung pada 200 sampel acak per dataset (seed 0). Teks emas harus dirutekan ke `finbert_emas`, teks FOMC ke `fomc_roberta`.

| Dataset | Akurasi routing |
|---|---|
| Emas (gold_sinha) | 94.00% |
| FOMC | 97.00% |

---

## Yang belum dievaluasi

- **Asosiasi sentimen ↔ harga**: dihitung terpisah oleh `cli stats` (OLS-HAC, Granger, CAR) dan disimpan di tabel `stat_results`. Belum ada yang signifikan setelah koreksi Benjamini-Hochberg.
- **Konsistensi persona**: uji monotonisitas yang dijanjikan `context/DESIGN.md` §12.4 belum diimplementasikan.
- **Kepatuhan alokasi**: total 100% dan batas min/max dijaga oleh tes, tetapi belum dilaporkan sebagai metrik.
