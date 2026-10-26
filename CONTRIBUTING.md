# CONTRIBUTING.md — Panduan Kontribusi

> Dokumen ini untuk **manusia** yang baru bergabung. Kalau Anda agen AI,
> baca `AGENTS.md` lebih dulu — di situ ada jalur navigasi yang lebih efisien.

Tujuan dokumen ini: membuat kontributor baru bisa menjalankan, mengubah, dan
memverifikasi repo ini tanpa harus bertanya. Setiap perintah di bawah sudah
diuji pada repo ini, bukan disalin dari tutorial.

---

## 1. Prasyarat

| Kebutuhan | Versi | Catatan |
|---|---|---|
| Python | **3.11** | Sesuai CI. 3.12 jalan, tetapi lihat §6 soal mypy. |
| Git | terbaru | Dataset besar di-track lewat Git LFS. |
| Docker | opsional | Hanya jika ingin menjalankan `docker-compose.yml`. |

Repo ini **tidak** butuh GPU untuk test. GPU (CUDA) hanya dipakai bila
melatih model atau memuat FOMC-RoBERTa.

---

## 2. Setup

```bash
git clone https://github.com/Josshua-DSA/ARCAS
cd ARCAS

python -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows (PowerShell)
# .\venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

### Variabel lingkungan

```bash
cp .env.example .env
```

Isi hanya kunci API yang Anda punya. `.env` **tidak** di-track git.
Kunci yang dikenal: `FINNHUB_API_KEY`, `MARKETAUX_API_KEY`,
`ALPHAVANTAGE_API_KEY`, `EULERPOOL_API_KEY`.

Tanpa kunci API, pengumpulan berita lewat RSS tetap bisa dijalankan. Jangan
mengarang nilai kunci — kode akan gagal dengan pesan yang jelas, dan itu
lebih baik daripada data palsu yang menyamar sebagai data asli.

---

## 3. Verifikasi sebelum commit

Tiga perintah. Semuanya harus lulus.

```bash
python -m pytest          # 384 passed, 2 skipped (baseline saat ini)
ruff check .              # harus "All checks passed!"
mypy                      # lihat §6 bila muncul error numpy
```

### Aturan test

- **Jangan menaikkan jumlah `skip`.** CI gagal bila lebih dari 5 test di-skip.
  Skip yang ada sekarang adalah kasus sah (data uji tanpa duplikat, bobot XAU
  sudah ada) — bukan alasan untuk menambah.
- **Test baru harus benar-benar menangkap bug.** Sebelum melaporkan selesai,
  matikan perbaikan Anda dan pastikan test-nya **gagal**. Test yang tetap
  hijau saat perbaikan dimatikan tidak membuktikan apa pun.
- **Jangan memakai `MagicMock` untuk data berlabel.** Bug arah sinyal di P0-2
  lolos berbulan-bulan justru karena test memakai skor buatan; kesalahan tanda
  tidak pernah terlihat. Pakai kalimat nyata dari dataset.

---

## 4. Konvensi commit

**Satu commit = satu berkas.** Ini diminta eksplisit oleh pemilik repo dan
bukan preferensi kosmetik: ia membuat `git blame`, `git revert`, dan review
per-berkas tetap mungkin dilakukan. Contoh urutan yang benar dari pekerjaan
P0:

```
8526a13 feat(config): tambah peta arah stance Fed per aset
d562fa3 feat(sentiment-config): baca dan validasi stance_direction
2c43384 fix(router): petakan skor stance ke arah harga per aset
0b4924f fix(pipeline): jadikan prioritas model eksplisit dan hemat memori
72ab725 test(router): kunci arah stance dan prioritas model
aef317b feat(fomc): tambah skrip training FOMC-RoBERTa
7c666ec docs(audit): catat penyelesaian P0 dan verifikasi model FOMC
```

### Urutan commit harus dependency-safe

Commit satu berkas berarti kode di tengah riwayat bisa setengah jadi. Karena
itu urutkan agar **setiap commit tetap bisa di-import**:

1. Konfigurasi/data (`data/*.yaml`)
2. Helper pembaca konfigurasi (`model/common/`)
3. Pemakai helper (`backend/src/...`)
4. Test
5. Skrip
6. Dokumentasi

Contoh nyata: `router.py` memakai `stance_direction` dari
`model/common/sentiment_config.py`, jadi helper itu **harus** di-commit lebih
dulu. Kalau dibalik, commit `router.py` akan gagal import.

### Format pesan

Conventional Commits: `type(scope): ringkasan imperatif`

`type`: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `perf`.

Badan pesan menjelaskan **kenapa**, bukan sekadar apa. Sebutkan bug yang
diperbaiki, bukti yang mendukung, dan cara memverifikasi. Nama berkas boleh
disebut; nomor baris sebaiknya tidak (cepat basi).

> **Peringatan teknis:** hindari backtick di pesan commit yang ditulis lewat
> `git commit -m "..."` di shell — isinya akan dieksekusi sebagai perintah
> dan hilang dari pesan. Pakai `git commit -F berkas.txt` untuk pesan panjang.

---

## 5. Aturan yang tidak boleh dilanggar

Ringkasan dari `context/RULES.md` — baca aslinya sebelum mengubah hal besar.

1. **Universe terkunci: `XAU`, `RATE_UST`, `SPX`.** Aset lain ditolak.
   Menambah/mengurangi aset = bump `universe_version` + catat di Changelog.
2. **`article_id` = SHA-256** dari teks ternormalisasi. Jangan diubah.
3. **Hari tanpa berita = `NULL`/`NaN`, bukan 0.** Nol berarti "sentimen
   netral", maknanya berbeda.
4. **Tidak ada magic number.** Ambang, cap, bobot, penalti harus di
   `data/sentiment_config.yaml`.
5. **Test set dikunci.** Val dipakai untuk threshold, temperature, early stop.
   Test dipakai sekali di akhir. Jangan memilih checkpoint berdasarkan test.
6. **Wajib baseline TF-IDF + Logistic Regression** lebih dulu; model kompleks
   hanya dipakai bila mengalahkannya secara bermakna (F1 macro + McNemar).
7. **Angka API gratis harus diverifikasi di situs resmi**, jangan dari blog.
8. **Jangan sentuh `frontend/`** bila tugas Anda di jalur backend/ML (dan
   sebaliknya) — kurangi konflik merge.

### Dua jebakan yang sudah memakan korban

- **FOMC-RoBERTa mengukur *stance* The Fed, bukan dampak harga.** Dovish
  berarti hawkishness negatif, dan dovish itu **bullish** untuk emas. Kode
  menyatakan jenis skor lewat `score_space`: `"stance"` untuk FOMC,
  `"price"` untuk FinBERT-EMAS. Salah menandai = arah sinyal terbalik.
  Lihat `backend/tests/test_p0_signal_direction.py`.
- **Checkpoint resmi `gtfintechlab/FOMC-RoBERTa` bersifat gated** (perlu
  login HF + setujui syarat). Kode otomatis fallback ke mirror publik
  `tim9510019/FOMC-RoBERTa`. Lisensinya **CC BY-NC 4.0 — non-komersial.**

---

## 6. Kalau mypy gagal karena numpy

Di Python 3.12 dengan numpy 2.x, mypy 1.11 gagal saat membaca stub numpy:

```
venv/lib/python3.12/site-packages/numpy/__init__.pyi:737: error:
Type statement is only supported in Python 3.12 and greater  [syntax]
```

Ini **bukan** kesalahan kode Anda. Stub numpy 2.x memakai sintaks `type`
statement yang tidak dipahami mypy 1.11 saat target versi 3.11. Terbukti:
error ini muncul identik pada commit sebelum perubahan apa pun (19 error di 5
berkas).

Solusi: jalankan dengan target 3.12.

```bash
mypy --python-version 3.12
```

Atau pakai Python 3.11 seperti CI. Jangan menaikkan versi mypy — `ruff` dan
`mypy` **dipin persis** di `requirements.txt` dengan sengaja: mypy 2.x tidak
melaporkan `[import-untyped]` yang dilaporkan 1.11, sehingga CI akan merah
padahal lokal hijau (atau sebaliknya).

---

## 7. Code graph (`.graphify/`)

Repo punya code graph untuk navigasi — **bukan** catatan riwayat kerja.

**Untuk membaca:** mulai dari `.graphify/GRAPH_REPORT.md`, lalu query:

```bash
./scripts/graph.sh explain "ModelRouter"
./scripts/graph.sh path "Article" "TargetImpact"
```

**Setelah mengubah kode**, dua perintah — bukan satu:

```bash
./scripts/graph.sh update .        # ekstraksi AST, gratis, tanpa LLM
./scripts/graph.sh cluster-only .  # regenerasi GRAPH_REPORT.md + graph.html
```

`update` **tidak** memperbarui laporan maupun `graph.html`; tanpa
`cluster-only` laporan tetap basi meski `graph.json` sudah segar.

Selalu pakai `./scripts/graph.sh`, jangan `graphify` langsung — tanpa wrapper,
`GRAPHIFY_OUT` tidak diset dan graf ditulis ke `graphify-out/`, menghasilkan
dua graf yang saling bertentangan.

Cek kesegaran graf dengan membandingkan baris `Built from commit:` di
`GRAPH_REPORT.md` dengan `git rev-parse --short HEAD`.

---

## 8. Melatih model

**Anda tidak perlu melatih apa pun untuk berkontribusi pada backend.** Bobot
yang ada sudah terverifikasi (FOMC: akurasi 0,8687 pada test holdout).

Bila memang perlu:

```bash
# FOMC — resep upstream (butuh ~6-7 GiB VRAM)
python -m scripts.train_fomc_roberta

# FOMC — hemat VRAM untuk GPU 6 GiB (efektif batch tetap 16)
python -m scripts.train_fomc_roberta --batch-size 4 --grad-accum 4

# XAU FinBERT
python -m scripts.train_xau_finbert
```

Flag `--base roberta-base` menghemat VRAM tetapi **bukan** reproduksi
upstream; `metrics.json` menandainya lewat `is_upstream_recipe`, jadi jangan
membandingkan angkanya langsung dengan 86,87%.

---

## 9. Menjalankan aplikasi

```bash
# API
uvicorn backend.src.serve.app:create_app --factory --host 0.0.0.0 --port 8000 --reload

# Kolektor berita
python -m backend.src.collect.news_cli health --json
python -m backend.src.collect.news_cli fetch --target XAU --dry-run
```

Jalur data lengkap: `docs/JALUR_DATA.md`.

---

## 10. Sebelum membuka Pull Request

- [ ] `python -m pytest` lulus, jumlah skip tidak bertambah
- [ ] `ruff check .` bersih
- [ ] mypy bersih (atau hanya error numpy di §6)
- [ ] Satu commit = satu berkas; urutan dependency-safe
- [ ] Test baru gagal bila perbaikan dimatikan
- [ ] Angka/klaim di pesan commit bisa direproduksi
- [ ] Code graph diregenerasi bila menyentuh kode
- [ ] Tidak ada kunci API, token, atau path absolut yang ikut ter-commit
