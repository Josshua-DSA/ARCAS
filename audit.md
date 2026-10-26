# Audit Teknis ARCAS — Backend, Model, Data & Infrastruktur

**Tanggal:** 2026-10-26
**Commit yang diaudit:** `b9550b3` (branch `perfected`)
**Cakupan:** `backend/`, `model/`, `data/`, `scripts/`, `dataset/`, `docs/`, CI, Docker, dependency
**Di luar cakupan:** `frontend/` — **tidak disentuh sesuai instruksi**

---

## 0. Ringkasan

> **Cara membaca dokumen ini:** temuan dikelompokkan per tingkat keparahan —
> **P0** (kritis, 3 item) · **P1** (penting, 6 item) · **P2** (sedang, 6 item) ·
> **P3** (ringan, 6 item). Total **21 temuan**. Untuk melihat semua item
> sekaligus, lompat ke §6 *Prioritas Perbaikan*.

| Aspek | Status | Catatan singkat |
|---|:---:|---|
| Test suite | ✅ **Sehat** | 369 passed, 2 skipped, 0 failed |
| Lint (ruff) | ✅ **Bersih** | `All checks passed!` |
| Type-check (mypy) | ✅ **Bersih** | Diperbaiki via `.python-version` (P1-3) |
| Coverage | ⚠️ **73%** | 1089 baris tak teruji dari 4105 (kode produksi saja) |
| Reproducibility | ✅ **Kuat** | `requirements-ci.lock` + `.python-version` (P1-2) |
| Keamanan | ⚠️ **Cukup** | Tidak ada secret ter-track; API tanpa auth |
| Integritas model | ⚠️ **Timpang** | XAU punya skrip training, FOMC tidak |

| Tingkat | Jumlah | Status |
|---|:---:|---|
| P0 — Kritis | 3 | ✅ **selesai semua** (2026-10-26) |
| P1 — Penting | 6 | 🟡 **2 selesai, 4 terbuka** |
| P2 — Sedang | 6 | ⬜ terbuka |
| P3 — Ringan | 6 | ⬜ terbuka |


**Kesimpulan satu baris:** fondasi backend solid dan teruji, tetapi **artefak model tidak dapat direproduksi** — tidak ada satu pun skrip yang bisa menghasilkan ulang angka di `benchmark_results.json` atau `metrics.json`.

---

## 1. Temuan Kritis (P0)

### P0-1 — FOMC-RoBERTa tidak punya skrip training sama sekali

> **STATUS: SELESAI (2026-10-26).** `scripts/train_fomc_roberta.py` ditambahkan
> mengikuti resep upstream (`roberta-large`, 3 kelas, dataset ACL 2023) dengan
> dukungan fp16 + gradient accumulation untuk GPU 6 GiB. Menulis bobot +
> `metrics.json` + `temperature.json`, memilih checkpoint menurut macro-F1
> validation, dan mengevaluasi holdout tanpa menyentuhnya saat pemilihan.
> Bobot belum dilatih (sesuai instruksi); angka 86,87% masih berasal dari
> checkpoint pihak ketiga sampai skrip ini dijalankan.

**Bukti:**

```
scripts/train_xau_finbert.py ................ ✅ ada
skrip training FOMC ......................... ❌ TIDAK ADA (pencarian `*fomc*` & `*train*`)
model/fomc/weights/ ......................... hanya baseline_fomc.joblib (312 KB) + temperature.json
```

Notebook `model/fomc/notebooks/03_fomc_roberta_exploration.ipynb` (21 cell) **tidak melatih RoBERTa**:

```
cell 6  -> melatih BASELINE TF-IDF (val acc 0.5928) -> baseline_fomc.joblib
cell 8  -> memuat checkpoint pretrained, ambil logits validasi
cell 10 -> kalibrasi suhu (T=2.1293)
```

Tidak ada `Trainer`, optimizer, epoch, atau loop training untuk RoBERTa. Tidak ada satu cell pun yang menulis bobot RoBERTa.

**Dampak:** angka `f1_macro 0.862` / `kappa 0.793` di `benchmark_results.json` **tidak dapat direproduksi dari repo ini**. Siapa pun yang mengkloning repo tidak bisa memperoleh model yang menghasilkan angka tersebut — hanya bisa mengunduh checkpoint pihak ketiga (`gtfintechlab` / mirror `tim9510019`) yang identitas dan lisensinya tidak terikat pada pekerjaan tim.

**Perbandingan dengan XAU:** `scripts/train_xau_finbert.py` ada, dan bobot lokal 440 MB ada. Track XAU lengkap; track FOMC tidak.

**Rekomendasi:**
1. Tambah `scripts/train_fomc_roberta.py` (atau notebook training terpisah) yang benar-benar fine-tune + menulis ke `model/fomc/weights/roberta/`.
2. Selama belum ada, beri label jelas di `benchmark_results.json` bahwa angka berasal dari checkpoint eksternal, bukan hasil training repo.

---

### P0-2 — Sinyal arah dovish/hawkish terbalik untuk aset yang diperdagangkan

> **STATUS: SELESAI (2026-10-26).** `data/sentiment_config.yaml` kini memuat
> `stance_direction` (`XAU: -1`, `RATE_UST: +1`, `SPX: -1`) dan
> `TargetRouter.route_article(..., score_space=...)` membedakan skor *stance*
> dari skor *harga*. Mode `stance` memetakan arah per aset; mode `price`
> (FinBERT-EMAS) berperilaku seperti sebelumnya. `impact_graph.yaml` tidak lagi
> dikalikan di mode `stance` agar arah tidak terbalik dua kali. Skor impact
> juga disimpan dalam ruang harga sehingga `direction` dan `score` konsisten.
> Dikunci oleh `backend/tests/test_p0_signal_direction.py` (15 test; 3 di
> antaranya gagal bila perbaikan dimatikan).

**Bukti (dijalankan langsung):**

| Input | Tone | p_pos | model |
|---|---|---|---|
| `decided to lower the target range` | negative | 0.113 | fomc_roberta |
| `decided to raise the target range` | positive | 0.956 | fomc_roberta |

Dokumentasi internal `model/fomc/src/model.py:213-215` menyatakan pemetaan ini **disengaja**:

```
LABEL_1 (Hawkish) -> p_pos (tightening / rates positive)
LABEL_2 (Neutral) -> p_neu
LABEL_0 (Dovish)  -> p_neg (easing / rates negative)
```

**Dampak:** model mengukur *stance* The Fed, bukan *dampak ke harga emas*. Untuk XAU, dovish umumnya **bullish** dan hawkish **bearish** — jadi tanda sinyal ini terbalik relatif terhadap instrumen yang diprediksi. Jika `impact_graph.yaml` mengalikan `sentiment_score` dengan sign target tanpa koreksi, arah rekomendasi untuk artikel FOMC akan salah.

Tidak ada test yang menangkap ini: seluruh test FOMC memakai `MagicMock` dengan skor buatan, sehingga kesalahan tanda tidak pernah muncul di suite.

**Rekomendasi:** putuskan secara eksplisit — (a) pertahankan semantik "stance" dan tambahkan langkah pembalik tanda di hilir sebelum masuk `impact_graph`, atau (b) definisikan ulang `p_pos`/`p_neg` sebagai dampak harga. Mana pun yang dipilih, **tambahkan test dengan kalimat dovish/hawkish nyata** yang mengunci arah.

---

### P0-3 — Prioritas model di pipeline implisit dan tidak terdokumentasi

> **STATUS: SELESAI (2026-10-26).** `backend/src/pipeline/runner.py` kini
> punya `MODEL_PRIORITY` (data eksplisit: FOMC sebelum FinBERT-EMAS) dengan
> `break`, dan model hanya dimuat bila benar-benar terpilih — FOMC 355M
> parameter tidak lagi dimuat lalu dibuang. Jika bobot sebuah model tidak
> tersedia, kandidat berikutnya dicoba. `score_space` ikut mengalir dari tabel
> ini ke router, sehingga P0-2 dan P0-3 memakai satu sumber kebenaran.
> Dikunci oleh `backend/tests/test_p0_signal_direction.py`.

**Bukti** (`backend/src/pipeline/runner.py:397-411`): blok `if "fomc_roberta"` ditulis **sebelum** `if "finbert_emas"`, keduanya menetapkan `selected_model` tanpa `break`, sehingga **yang terakhir menang** — XAU selalu mengalahkan FOMC.

Terbukti lewat routing nyata:

```
src=reuters | "Gold prices surge as Fed signals rate cuts."  -> ['finbert_emas', 'fomc_roberta']
src=kitco   | "Gold prices surge as Fed signals rate cuts."  -> ['finbert_emas']
src=reuters | "Bullion rallies after Powell comments."       -> ['finbert_emas', 'fomc_roberta']
```

Untuk artikel yang memicu **keduanya**, FOMC dimuat (biaya 355M parameter) lalu **dibuang** tanpa dipakai.

**Dampak:** (1) pemborosan komputasi; (2) perilaku bergantung urutan penulisan `if` — refactor kecil bisa diam-diam membalik prioritas; (3) artikel emas yang sangat dipengaruhi Fed dinilai hanya dengan FinBERT-EMAS, padahal FOMC justru model yang lebih relevan untuk dimensi kebijakan moneter.

**Rekomendasi:** jadikan prioritas eksplisit dan teruji, misalnya tabel `MODEL_PRIORITY = ["fomc_roberta", "finbert_emas"]` dengan `break`, lalu tambah test untuk artikel yang memicu dua model.

---

## 2. Temuan Penting (P1)

> **Status per 2026-10-26: 2 dari 6 selesai** — P1-2 dan P1-3 ✅.
> Sisa P1-1, P1-4, P1-5, P1-6 masih terbuka. Urutan pengerjaan ada di §6.

### P1-1 — Artefak bobot tidak di-vendor, inferensi bergantung jaringan

`.gitignore` mengecualikan `model/*/weights/*/`, `*.bin`, `*.safetensors`, `*.pt`, `*.onnx`.

- **XAU:** bobot ada di disk lokal (440 MB) tapi **tidak di-track** — mesin baru harus melatih sendiri (± butuh GPU + waktu).
- **FOMC:** tidak punya bobot sendiri; bergantung pada unduhan dari HF Hub saat runtime.

Konsekuensi: `load_fomc_model()` mengembalikan `None` saat offline, dan pipeline **diam-diam** jatuh ke baseline 57,98% alih-alih RoBERTa 86,87%. Tidak ada log level-warning yang membedakan "sengaja fallback" dari "gagal karena masalah".

**Rekomendasi:** gunakan Git LFS untuk bobot terlatih, atau sediakan `scripts/fetch_weights.py` dengan checksum SHA256 agar unduhan terverifikasi.

### P1-2 — Tidak ada lock file; pin dependency longgar — ✅ **SELESAI**

**Status: SELESAI** (2026-10-26) · commit `616d04d`, `957b15a`

```
requirements.txt: torch>=2.0.0, transformers>=4.30.0, numpy>=1.26.0
lock file: TIDAK ADA (tidak ada poetry.lock / uv.lock / pip.lock / requirements.lock)
```

Ini bukan teori — sudah menimbulkan bug nyata. `torch 2.5.1` menolak memuat `pytorch_model.bin` karena CVE-2025-32434, dan perbaikannya butuh kerja manual. Dengan lock file, kejadian ini terdeteksi sebelum merge.

**Yang dikerjakan:**

1. **`requirements-ci.lock`** — mengunci versi persis dependensi tingkat atas. Bukan `pip freeze` mentah: tanpa penanda build lokal (`+cu121` akan menggagalkan runner CPU), dan `torch`/`transformers` dikunci pada versi yang **diuji** (2.5.1 / 4.57.6), bukan yang terbaru — dibiarkan, pip memilih torch 2.14 dan transformers 5.x yang belum pernah dijalankan terhadap kode ini.
2. **`requirements.txt` dilengkapi.** Empat paket dipakai kode/test tetapi tidak pernah ada di manifest: `scikit-learn`, `joblib`, `pyarrow`, `openpyxl`. Semuanya lolos di mesin pengembang karena terpasang di luar manifest; di lingkungan bersih kegagalannya berupa collection error sebelum satu test pun jalan.
3. **CI memasang** `-r requirements.txt -r requirements-ci.lock`.

**Koreksi penting terhadap rekomendasi di atas.** Audit menyarankan `numpy<3`. Saya sempat mencoba `numpy<2.0` dengan alasan menghindari kegagalan mypy, dan **itu terbukti merusak**:

```
ImportError: pyarrow requires NumPy 2.0 or newer, found 1.26.4
```

9 test gagal. Batas `<3.0` memang yang benar — dan penyebab kegagalan mypy ternyata bukan numpy sama sekali (lihat P1-3).

**Verifikasi:** venv Python 3.11 dibuat ulang dari nol → `pip install -r requirements.txt -r requirements-ci.lock` exit 0 → `mypy` `Success: no issues found in 62 source files` → seluruh test suite lulus.

**Batasan yang jujur:** `seaborn` tidak terpasang di environment sumber, sehingga tidak dicantumkan di lock alih-alih dikarang versinya. CI memasang versi terbaru dari rentang.

### P1-3 — mypy gagal di lingkungan developer, hijau di CI — ✅ **SELESAI**

**Status: SELESAI** (2026-10-26) · commit `3ebc94a`, `c45ff70`

```
lokal : Found 4 errors in 4 files — types-PyYAML TIDAK terpasang,
        numpy 2.5.4 membuat mypy 1.11 gagal parse stub (Python 3.12)
CI    : success (Python 3.11, dependency ter-resolve saat itu)
```

`RULES §4` mewajibkan "ruff + mypy bersih sebelum merge", tetapi kontributor di Python 3.12 + numpy 2.x **tidak bisa memenuhinya** tanpa menyentuh `venv` secara manual. Gerbang mutu jadi tidak dapat dijalankan lokal.

**Diagnosis yang benar** — menggantikan dugaan awal "3.12 vs 3.11". Empat kombinasi diuji di venv terisolasi:

| Python | numpy | mypy 1.11.2 |
|---|---|---|
| 3.11 | 2.4.6 | ✅ Success (kondisi CI) |
| 3.11 | 1.26.4 | ✅ Success |
| 3.12 | 1.26.4 | ✅ Success |
| 3.12 | 2.5.4 | ❌ syntax error (venv pengembangan) |

Pemicunya **python 3.12 DAN numpy 2.x bersamaan**, bukan salah satunya. Stub `numpy/__init__.pyi` 2.x memakai sintaks `type X = ...` (PEP 695) di dalam cabang `sys.version_info >= (3, 12)`. mypy 1.11 tidak bisa mem-parse sintaks itu sama sekali — bahkan saat target versi 3.11 — sehingga ia berhenti **sebelum** memeriksa satu berkas proyek pun. Pada target 3.11 baris itu tidak dibaca, karena itulah CI tidak pernah terkena.

**Yang dikerjakan:** `.python-version` berisi `3.11`, dibaca otomatis oleh pyenv. Dev tidak perlu mengingat versi apa pun, dan gerbang mutu yang ia jalankan identik dengan yang menentukan lulus/gagal merge. `CONTRIBUTING.md` §6 diperbaiki: saran lama `mypy --python-version 3.12` **salah** — pada kondisi itu justru gagal.

> ⚠️ **Sisa tindakan (tidak bisa diotomatiskan):** `.python-version` **tidak** memperbaiki venv yang sudah terlanjur dibuat dengan Python 3.12. Venv lama harus dibuat ulang:
>
> ```bash
> rm -rf venv && python3.11 -m venv venv
> ./venv/bin/pip install -r requirements.txt -r requirements-ci.lock
> ```
>
> Tanpa itu, `./venv/bin/mypy` tetap gagal di mesin yang venv-nya 3.12 — meski `ruff` dan test suite tetap lulus di sana (`ruff`: `All checks passed!`; pytest: hanya 2 skip, 0 gagal).

**Alternatif yang ditolak:** menaikkan mypy ke 2.x. Itu mengubah gerbang mutu diam-diam, karena mypy 2.x tidak melaporkan `[import-untyped]` yang dilaporkan 1.11.


### P1-4 — Tidak ada test yang membuktikan RoBERTa benar-benar dipakai

Seluruh `test_fomc_pipeline_integration.py` memakai `MagicMock` untuk model:

```python
mock_fomc = MagicMock()
pipeline.fomc_model = mock_fomc
```

Tidak ada satu test pun yang memuat model nyata dan memverifikasi `probs[0].model == "fomc_roberta"`. Inilah sebabnya bug "RoBERTa tidak pernah aktif" (ditemukan kemarin) bisa lolos: suite **selalu hijau** apakah RoBERTa hidup atau mati.

**Rekomendasi:** tambah satu *smoke test* bertanda `@pytest.mark.slow` / `@pytest.mark.network` yang memuat model nyata untuk 2 kalimat dan mengunci `model == "fomc_roberta"`. Default suite tetap offline.

### P1-5 — Evaluasi & metrik statistik tidak teruji

```
model/xau/evaluation/evaluate.py ............ 0%   (83 baris, 0 teruji)
model/common/train_baseline.py .............. 0%   (51 baris)
model/common/01_baseline_exploration.py ..... 0%   (24 baris)
model/common/metrics.py ..................... 38%
model/fomc/evaluation/evaluate_holdout.py ... 52%
```

`compute_multiclass_ece`, `compute_mcnemar_test`, `compute_bootstrap_ci` **hanya diuji di `test_fomc_track.py`**. Padanan XAU-nya tidak teruji sama sekali. Artinya angka ECE, p-value McNemar, dan CI bootstrap yang dilaporkan untuk XAU tidak diverifikasi.

**Rekomendasi:** angkat fungsi metrik ke `model/common/metrics.py` (sebagian sudah di sana) dan uji sekali untuk kedua track. Saat ini fungsi serupa terduplikasi antar dua skrip evaluasi.

### P1-6 — Duplikasi fixture `temp_db` dan tidak ada `conftest.py`

`temp_db` didefinisikan ulang di 3 file test berbeda, dan repo **tidak punya `conftest.py`** sama sekali.

**Rekomendasi:** satu `backend/tests/conftest.py` dengan fixture bersama.

---

## 3. Temuan Sedang (P2)

### P2-1 — Endpoint API tanpa autentikasi

8 route di `backend/src/serve/app.py` (`/health`, `/api/meta`, `/api/universe`, `/api/series/{target}`, `/api/impacts/{target}`, `/api/stats/{target}`, `/api/allocation`, `/api/persona/{article_id}`) tidak memiliki `Depends`, API key, maupun Authorization header.

Wajar untuk dashboard internal; **berisiko** jika `Dockerfile` (EXPOSE 8000) dipublikasikan. Tidak ada rate limiting.

### P2-2 — Coverage 73%, bagian terlemah di jalur kolektor

**Coverage kode produksi (`backend/src` + `model` saja, test dikecualikan): 73% — 1089 dari 4105 baris tak teruji.**

| File | Cover |
|---|---|
| `collect/news_api/marketaux.py` | 29% |
| `collect/news_api/alphavantage.py` | 31% |
| `collect/news_api/client.py` | 35% |
| `collect/news_cli.py` | 40% |
| `collect/news_api/finnhub.py` | 43% |
| `collect/news_api/registry.py` | 49% |
| `backend/src/cli.py` | 53% |
| `collect/rss_collector.py` | 58% |
| `serve/app.py` | 66% |
| `pipeline/runner.py` | 83% |

Sebaliknya, 26 modul sudah **100%** — termasuk `normalize/dedup.py`, `persona/engine.py`, `schema.py` (99%), `quota.py` (97%), `keywords.py` (93%). Jadi mutu tidak merata: inti deterministik sangat teruji, adaptor jaringan tidak.

Jalur yang menyentuh **API eksternal berbayar** justru paling sedikit teruji — padahal di situ kuota dan parsing error paling mahal. `eulerpool.py` (64%) punya penanganan kuota yang tidak tercakup penuh.

### P2-3 — Duplikasi `compute_mcnemar_test` / `compute_bootstrap_ci`

Fungsi statistik diimplementasikan ulang di `model/fomc/evaluation/evaluate_holdout.py` dan variannya, bukan dipakai bersama dari `model/common/`. Risiko: perbaikan di satu tempat tidak merambat ke tempat lain.

### P2-4 — Dokumentasi tidak sinkron dengan kode

| Dokumen | Klaim | Kenyataan |
|---|---|---|
| `AGENTS.md:163` | "`model/xau/src/` masih kosong" | Berisi 3 modul + bobot 440 MB, sudah jalan |
| `AGENTS.md:66` | Track XAU sebagai tabel | Ada, tapi status "kosong" menyesatkan |
| `model/fomc/README.md` | mirror otomatis dipakai | **Baru benar setelah commit `b9550b3`**; sebelumnya klaim tanpa implementasi |

`AGENTS.md` adalah dokumen yang dibaca agen/kontributor **sebelum** menyentuh repo, sehingga informasi basi di sini berbiaya tinggi.

### P2-5 — `.graphify/` ter-track di git (±2,9 MB artefak generate)

```
.graphify/graph.json  1588 KB
.graphify/graph.html  1356 KB
.graphify/GRAPH_REPORT.md, manifest.json, .graphify_labels.json
```

Artefak hasil generate ikut masuk version control. Menambah noise pada diff dan memperbesar `.git` (29 MB — juga memuat `research/papers/*.pdf` ±7 MB).

### P2-6 — Test pollution: `test_protokol_terpenuhi` gagal karena VRAM, bukan logika

Test `backend/tests/test_xau_track.py::TestTrainedModel::test_protokol_terpenuhi` **lulus sendiri** tapi gagal di suite penuh dengan `CUDA out of memory` (GPU 6 GiB). Test ini memuat model nyata dan bersaing VRAM dengan test lain.

Sudah dimitigasi untuk FOMC (default CPU, `FOMC_DEVICE=cuda` untuk memaksa), tetapi **XAU masih rentan** terhadap kondisi yang sama jika suite bertambah.

**Rekomendasi:** beri mark `slow`/`gpu` dan jalankan terpisah, atau paksa `device="cpu"` di test.

---

## 4. Temuan Ringan (P3)

| # | Temuan | Bukti |
|---|---|---|
| P3-1 | `datetime.utcnow()` deprecated | 10 kemunculan di `backend/src` + `model`; memicu `DeprecationWarning` di suite |
| P3-2 | `except ... : pass` menelan error | 4 lokasi: `rss_collector.py:102`, `news_api/client.py:123`, `registry.py:90`, `eulerpool.py:54` |
| P3-3 | Tidak ada penanda TODO/FIXME | 0 kemunculan — baik, tapi juga berarti utang teknis tidak dilacak eksplisit |
| P3-4 | `dataset/` + `research/papers/` di-track (PDF & parquet ±9 MB) | Membesarkan repo tanpa manfaat runtime |
| P3-5 | Tidak ada migrasi/seed DB | Skema SQLite dibuat di kode; perubahan skema tidak punya jalur upgrade |
| P3-6 | `.env.example` ada, `.env` tidak ter-track | ✅ aman; tidak ada API key hardcoded (diverifikasi regex) |

---

## 5. Yang Sudah Baik (jangan diubah)

1. **Komentar audit bernomor** (`AUDIT K-4`, `S-1`, `S-2`, `FR-6`) yang menjelaskan *mengapa* kode begitu — jarang ditemukan dan sangat membantu.
2. **Fail-loud pada model hilang**: `load_model()` melempar `PipelineError` alih-alih lanjut dengan angka kosong (`AUDIT K-4`).
3. **Endpoint `/api/allocation` sudah tidak menyajikan angka karangan** — skor diambil dari `daily_sentiment`, dengan `data_sources` terbuka (`S-1`). Ini perbaikan integritas yang benar.
4. **CI mem-pin versi ruff & mypy** dan menolak mypy 2.x dengan alasan yang dijelaskan — praktik yang matang.
5. **Healthcheck Docker** berfungsi (`/health`, interval 30s).
6. **Retry/timeout ada di kolektor** (21 kemunculan; `timeout=20.0`, `max_retries`).
7. **Tidak ada secret ter-track**, `.env` di-gitignore, tidak ada API key hardcoded.
8. **Test suite tidak butuh jaringan** — semua host contoh memakai `.test`.
9. **369 test hijau, ruff bersih.**

---

## 6. Prioritas Perbaikan

> Kolom **Status** ditambahkan 2026-10-26. Tanda ✅ berarti sudah dikerjakan
> dan diverifikasi; rinciannya ada di bagian temuan masing-masing.

| Prioritas | Item | Usaha | Dampak | Status |
|---|---|---|---|---|
| **P0-1** | Skrip training FOMC-RoBERTa | Besar | Reproducibility hilang total tanpa ini | ✅ |
| **P0-2** | Putuskan & uji arah dovish/hawkish | Kecil | Arah sinyal bisa terbalik | ✅ |
| **P0-3** | Prioritas model eksplisit di pipeline | Kecil | Pemborosan + perilaku rapuh | ✅ |
| **P1-1** | Vendor bobot via LFS / fetch ber-checksum | Sedang | Inferensi offline | ⬜ |
| **P1-2** | Lock file + batas `numpy<3` | Kecil | Mencegah bug dependency | ✅ |
| **P1-3** | Samakan Python dev/CI | Kecil | Gerbang mutu bisa dijalankan lokal | ✅ |
| **P1-4** | Smoke test model nyata | Kecil | Menangkap "fallback diam-diam" | ⬜ |
| **P1-5** | Uji metrik XAU (ECE/McNemar/bootstrap) | Sedang | Angka evaluasi terverifikasi | ⬜ |
| **P1-6** | `conftest.py` bersama | Kecil | Mengurangi duplikasi | ⬜ |
| **P2-1** | Auth/rate limit API | Kecil | Keamanan saat dipublikasikan | ⬜ |
| **P2-2** | Test kolektor API berbayar | Sedang | Kuota & parsing error | ⬜ |
| **P2-3** | Hapus duplikasi `compute_mcnemar_test` / `compute_bootstrap_ci` | Kecil | Satu sumber kebenaran metrik | ⬜ |
| **P2-4** | Perbarui `AGENTS.md` | Kecil | Info basi berbiaya tinggi | ⬜ |
| **P2-5** | Keluarkan `.graphify/` dari git atau beri batas ukuran | Kecil | Repo membengkak, diff berisik | ⬜ |
| **P2-6** | Isolasi test `test_protokol_terpenuhi` dari VRAM | Kecil | Test gagal karena lingkungan, bukan logika | ⬜ |
| **P3-*** | `utcnow`, `except: pass`, kebersihan lain (6 item) | Kecil | Kebersihan | ⬜ |

**Usulan urutan pengerjaan P1** (dari yang paling murah dan berdampak):

1. **P1-2 + P1-3** — satu paket, keduanya soal dependency/Python. Menutup
   penyebab mypy merah di lokal sekaligus menutup celah `numpy 2.x`.
2. **P1-4** — smoke test yang memastikan RoBERTa benar-benar dipakai, bukan
   fallback diam-diam. Ini yang paling berbahaya karena kegagalannya senyap.
3. **P1-1** — vendor bobot atau fetch ber-checksum; bergantung keputusan Anda
   soal ukuran repo (bentrok dengan P2-5).
4. **P1-6** lalu **P1-5** — `conftest.py` dulu agar helper uji metrik tidak
   terduplikasi saat menulis test baru.


---

## 7. Cara Mereproduksi Audit Ini

```bash
cd ~/Documents/FInews && git checkout perfected

# Kesehatan dasar
./venv/bin/python -m pytest                      # 369 passed, 2 skipped
./venv/bin/ruff check .                          # All checks passed

# Type-check (akan GAGAL di Python 3.12 + numpy 2.x — lihat P1-3)
./venv/bin/python -m mypy

# Coverage
./venv/bin/python -m pytest --cov=backend --cov=model --cov-report=term-missing

# Bukti arah sinyal FOMC (P0-2)
./venv/bin/python -c "
from model.fomc.src.model import FOMCRoBERTaSentiment
m = FOMCRoBERTaSentiment()
r = m.score_article('a1','The Committee decided to lower the target range for the federal funds rate.')
print(r.tone, r.probs[0].model)"

# Bukti prioritas model (P0-3)
./venv/bin/python -c "
from backend.src.tagging.model_router import ModelRouter
print(ModelRouter().route('Gold prices surge as Fed signals rate cuts.', source='reuters')[0])"

# Bukti tidak ada skrip training FOMC (P0-1)
find . -name '*fomc*' -not -path './venv/*' -not -path './.git/*'
```

---

## 8. Catatan Metodologi

- Seluruh temuan di atas **diverifikasi dengan menjalankan perintah**, bukan dari membaca dokumentasi. Klaim dokumentasi yang bertentangan dengan eksekusi dicatat sebagai temuan (P2-4).
- `frontend/` tidak diperiksa sesuai instruksi.
- Coverage diukur pada `backend/src` + `model` saja (file test dikecualikan). Angka **73%** (1089/4105 baris tak teruji) berbeda dari 83% yang sempat muncul saat pemindaian awal — selisih itu berasal dari file `backend/tests/` yang ikut terhitung sebagai "tercakup". Angka 73% yang dipakai di sini adalah angka yang benar untuk kode produksi.
- Audit ini tidak mengubah kode. Satu-satunya perubahan repo terkait adalah commit `b9550b3` yang sudah ada sebelumnya.
