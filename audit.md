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
| P1 — Penting | 6 | ✅ **selesai semua** (P1-5: 59 baris I/O belum bisa diuji offline) |
| P2 — Sedang | 6 | 🟡 **3 selesai, 3 terbuka** (P2-1, P2-2, P2-5) |
| P3 — Ringan | 6 | 🟡 **3 selesai, 1 terbuka, 2 bukan cacat** (P3-4 terbuka) |


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

> **Status per 2026-10-26 (lanjutan): 6 dari 6 selesai** — P1-2, P1-3,
> P1-1, P1-4, P1-6, dan P1-5 ✅. Catatan P1-5: McNemar/bootstrap XAU kini
> terverifikasi lewat modul metrik bersama; 59 baris I/O `evaluate.py`
> tetap tak teruji karena butuh bobot 440 MB (bukan metrik yang dilaporkan).

### P1-1 — Artefak bobot tidak di-vendor, inferensi bergantung jaringan — ✅ **SELESAI**

`.gitignore` mengecualikan `model/*/weights/*/`, `*.bin`, `*.safetensors`, `*.pt`, `*.onnx`.

- **XAU:** bobot ada di disk lokal (440 MB) tapi **tidak di-track** — mesin baru harus melatih sendiri (± butuh GPU + waktu).
- **FOMC:** tidak punya bobot sendiri; bergantung pada unduhan dari HF Hub saat runtime.

Konsekuensi: `load_fomc_model()` mengembalikan `None` saat offline, dan pipeline **diam-diam** jatuh ke baseline 57,98% alih-alih RoBERTa 86,87%. Tidak ada log level-warning yang membedakan "sengaja fallback" dari "gagal karena masalah".

**Rekomendasi:** gunakan Git LFS untuk bobot terlatih, atau sediakan `scripts/fetch_weights.py` dengan checksum SHA256 agar unduhan terverifikasi.

**Status: SELESAI** (2026-10-26) · commit `b9ccb68` — rekomendasi kedua yang dipakai.

1. **`scripts/fetch_weights.py`** — unduh + verifikasi SHA256 tiap berkas.
   Checksum diambil dari bobot yang sudah terbukti lulus smoke test, bukan
   dari dokumentasi pihak ketiga. Checksum salah = **exit 1**, bukan
   peringatan yang bisa dilewat. Mode: `--all`, `--model`,
   `--verify-only` (offline, untuk CI), `--print-checksums`.
   Diuji negatif: merusak 1 byte `config.json` → exit 1; dipulihkan → exit 0.
2. **Fallback tidak lagi senyap** — `load_fomc_model()` mencatat kegagalan ke
   `self._degradasi`, diteruskan ke `PipelineStats.errors` sehingga muncul di
   `ringkas()` yang dicetak CLI. Ketiadaan `torch`/`transformers` juga dicatat
   eksplisit. Sebelumnya hanya `logger.warning` — mudah terlewat di cron/CI.

Keputusan: **Git LFS tidak dipakai.** Bobot tetap di-`ignore`; yang di-vendor
adalah cara mengambilnya secara terverifikasi. Ini juga menghindari bentrok
dengan P2-5 soal ukuran repo.

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


### P1-4 — Tidak ada test yang membuktikan RoBERTa benar-benar dipakai — ✅ **SELESAI**

**Status: SELESAI** (2026-10-26) · commit `5fb4abe`

`backend/tests/test_fomc_roberta_real.py` — 6 test memuat model **nyata** dari
cache HuggingFace (bukan `MagicMock`): `model_name`/`model_version` bukan
baseline, invarian probabilitas (tiap p ∈ [0,1], total 1.0), kalimat hawkish
condong `p_pos` (menangkap pemetaan label terbalik), batch == single
(menangkap bug padding/masking), dan lewat `Pipeline` mengunci
`model_version == "fomc-roberta-v1.0"` serta `routed_from` menyebut
`fomc_roberta`.

Marker `slow`+`network` didaftarkan di `pyproject.toml` dan dikecualikan dari
suite default, sehingga default tetap offline. Menjalankan eksplisit:
`pytest -m "slow or network" backend/tests/test_fomc_roberta_real.py` →
**6 passed**.

Catatan: checkpoint primer `gtfintechlab/FOMC-RoBERTa` sedang dibatasi di HF,
sehingga jalur fallback `tim9510019/FOMC-RoBERTa` yang dipakai. Itu perilaku
kode yang sudah ada, dan test membuktikannya bekerja.

Seluruh `test_fomc_pipeline_integration.py` memakai `MagicMock` untuk model:

```python
mock_fomc = MagicMock()
pipeline.fomc_model = mock_fomc
```

Tidak ada satu test pun yang memuat model nyata dan memverifikasi `probs[0].model == "fomc_roberta"`. Inilah sebabnya bug "RoBERTa tidak pernah aktif" (ditemukan kemarin) bisa lolos: suite **selalu hijau** apakah RoBERTa hidup atau mati.

**Rekomendasi:** tambah satu *smoke test* bertanda `@pytest.mark.slow` / `@pytest.mark.network` yang memuat model nyata untuk 2 kalimat dan mengunci `model == "fomc_roberta"`. Default suite tetap offline.

### P1-5 — Evaluasi & metrik statistik tidak teruji — ✅ **SELESAI** (sisa: 59 baris I/O)

**Status: SELESAI** (2026-10-26) · commit `f1a9025`, `2cdc623`

| Berkas | Sebelum | Sesudah |
|---|---|---|
| `model/common/metrics.py` | 38% | **94%** |
| `model/xau/evaluation/evaluate.py` | 0% | **31%** |

- Metrik diangkat ke `model/common/metrics.py` dan diuji sekali untuk kedua
  track (`backend/tests/test_metrics.py`, 15 test).
- **McNemar dan bootstrap memang sudah terverifikasi.** `test_metrics.py`
  menguji keduanya secara langsung lewat import bersama
  (`compute_mcnemar_test`, `compute_bootstrap_ci`), menggantikan import lama
  dari `model/fomc/evaluation/evaluate_holdout.py` di `test_fomc_track.py`.
  Cakupannya: kasus manual terhitung benar, hanya diadopsi bila signifikan
  **dan** lebih baik, tanpa selisih = tidak signifikan, tabel kontingensi
  konsisten dengan n, reproducible dengan seed sama, model identik = selisih
  nol, dan seed berbeda memberi hasil sedikit berbeda. Karena fungsi kini
  dipakai bersama, pengujian ini berlaku untuk **kedua** track.
- `evaluate.py` dipecah: `softmax_with_temperature()` dan `build_report()`
  kini fungsi murni yang bisa diuji tanpa memuat model 440 MB.
- `backend/tests/test_xau_evaluation.py` (16 test) mengunci **angka**:
  akurasi 3/4-benar = 0.75, prediksi sempurna → macro-F1 1.0, confusion
  matrix baris=aktual/kolom=prediksi, argmax tidak berubah oleh suhu, dan
  `meets_target` memakai ECE **sesudah** kalibrasi (salah pilih kolom akan
  membuat laporan berbohong).
- Refaktor dibuktikan **tidak menggeser angka**: `eval_report.json` tidak
  berubah (accuracy 0.951744, macro_f1 0.888703, temperature 1.34559,
  ece_post 0.007386).

**Sisa yang masih terbuka (bukan bagian dari klaim metrik):**

- 59 baris `evaluate.py` (`112-155`, `165-199`, `203`): pemuatan
  `torch`/`transformers`, loop inferensi batch, `main()`, `_print_summary()`.
  Semua butuh bobot 440 MB; tidak bisa diuji di CI offline.
- `model/common/train_baseline.py` (0%) dan `01_baseline_exploration.py` (0%)
  tetap 0% — keduanya skrip eksplorasi, bukan metrik yang dilaporkan.
- `compute_multiclass_ece` masih tinggal di `model/fomc/src/calibrator.py`
  sementara ECE skalar ada di `model/common/metrics.py`. Ini duplikasi
  konseptual yang sebaiknya disatukan (bersinggungan dengan P2-3).

```
model/xau/evaluation/evaluate.py ............ 0%   (83 baris, 0 teruji)
model/common/train_baseline.py .............. 0%   (51 baris)
model/common/01_baseline_exploration.py ..... 0%   (24 baris)
model/common/metrics.py ..................... 38%
model/fomc/evaluation/evaluate_holdout.py ... 52%
```

`compute_multiclass_ece`, `compute_mcnemar_test`, `compute_bootstrap_ci` **hanya diuji di `test_fomc_track.py`**. Padanan XAU-nya tidak teruji sama sekali. Artinya angka ECE, p-value McNemar, dan CI bootstrap yang dilaporkan untuk XAU tidak diverifikasi.

**Rekomendasi:** angkat fungsi metrik ke `model/common/metrics.py` (sebagian sudah di sana) dan uji sekali untuk kedua track. Saat ini fungsi serupa terduplikasi antar dua skrip evaluasi.

### P1-6 — Duplikasi fixture `temp_db` dan tidak ada `conftest.py` — ✅ **SELESAI**

**Status: SELESAI** (2026-10-26) · commit `f84edfb`

`backend/tests/conftest.py` sekarang berisi fixture bersama; `def temp_db`
hanya ada di satu tempat (sebelumnya diduplikasi di 3 file test).
Diverifikasi: `grep -rln "def temp_db" backend/tests/` → hanya
`backend/tests/conftest.py`.

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

### P2-3 — Duplikasi `compute_mcnemar_test` / `compute_bootstrap_ci` — ✅ **SELESAI**

**Status: SELESAI** (sebelum audit ini diperbarui) · commit `f1a9025`

Diverifikasi ulang: fungsi kini hanya ada di `model/common/metrics.py`
(`:82`, `:133`). `model/fomc/evaluation/evaluate_holdout.py:23` mengimpornya
dari sana (`from model.common.metrics import compute_bootstrap_ci,
compute_mcnemar_test`), dan `backend/tests/test_metrics.py` menguji keduanya
lewat jalur bersama itu. Tidak ada implementasi kedua yang tersisa.

### P2-4 — Dokumentasi tidak sinkron dengan kode — ✅ **SELESAI**

**Status: SELESAI** (2026-10-26)

| Dokumen | Klaim lama | Kenyataan |
|---|---|---|
| `AGENTS.md:163` | "`model/xau/src/` masih kosong" | **Salah.** Berisi `model.py` + `data_loader.py`, bobot terlatih (`test_macro_f1` 0,8887) |
| `AGENTS.md` §7 | Track XAU tidak disebut di daftar "sudah ada" | Sudah ditambahkan |
| `model/fomc/README.md` | mirror otomatis dipakai | **Baru benar setelah commit `b9550b3`** |

Dua rujukan mati ke `context/AUDIT.md` (dihapus pemilik) juga diperbaiki:
`AGENTS.md:146` dan `backend/tests/test_manual_ingest.py:3` kini menunjuk
`audit.md` di root repo.

`AGENTS.md` adalah dokumen yang dibaca agen/kontributor **sebelum** menyentuh repo, sehingga informasi basi di sini berbiaya tinggi.

### P2-5 — `.graphify/` ter-track di git (±2,9 MB artefak generate)

```
.graphify/graph.json  1588 KB
.graphify/graph.html  1356 KB
.graphify/GRAPH_REPORT.md, manifest.json, .graphify_labels.json
```

Artefak hasil generate ikut masuk version control. Menambah noise pada diff dan memperbesar `.git` (29 MB — juga memuat `research/papers/*.pdf` ±7 MB).

### P2-6 — Test pollution: `test_protokol_terpenuhi` gagal karena VRAM, bukan logika — ✅ **SELESAI**

**Status: SELESAI** (2026-10-26)

Test `backend/tests/test_xau_track.py::TestTrainedModel::test_protokol_terpenuhi` **lulus sendiri** tapi gagal di suite penuh dengan `CUDA out of memory` (GPU 6 GiB). Test ini memuat model nyata dan bersaing VRAM dengan test lain.

Yang dikerjakan (rekomendasi audit dijalankan keduanya):

- `TestTrainedModel` diberi `@pytest.mark.slow`, sehingga keluar dari suite
  default (`-m "not slow and not network"`).
- `test_protokol_terpenuhi` memanggil `FinbertGoldSentiment(device="cpu")`
  secara eksplisit, bukan membiarkan auto-deteksi CUDA di dalam model.

Bukti: suite default **420 passed, 2 skipped, 8 deselected**; dijalankan
eksplisit `pytest -m slow backend/tests/test_xau_track.py` → **2 passed**
(4,47s). Jumlah deselected naik dari 6 ke 8 karena 2 test inilah yang pindah
jalur — bukan test yang hilang.

---

## 4. Temuan Ringan (P3)

**Status per 2026-10-28: P3-1, P3-2, P3-5 selesai.** P3-5 ditutup lewat PR #32
(merge `a5efbdd`); lihat `context/SCHEMA.md` §6.1. P3-3 (tidak ada TODO/FIXME) adalah observasi, bukan cacat.
P3-4 tetap terbuka.

| # | Temuan | Bukti | Status |
|---|---|---|---|
| P3-1 | `datetime.utcnow()` deprecated | `schema.py:159`, `:258` + `test_schema.py` | ✅ diganti `datetime.now(timezone.utc)`; 0 warning `utcnow` |
| P3-2 | `except ... : pass` menelan error | 4 lokasi (lihat bawah) | ✅ semua diberi log DEBUG |
| P3-3 | Tidak ada penanda TODO/FIXME | 0 kemunculan | observasi, bukan cacat |
| P3-4 | `dataset/` + `research/papers/` di-track (PDF & parquet ±9 MB) | membesarkan repo | ⬜ terbuka |
| P3-5 | Tidak ada migrasi/seed DB | skema dibuat di kode | ✅ `user_version` + `KOLOM_WAJIB` per-tabel + seed idempoten + `fi check-schema` |
| P3-6 | `.env.example` ada, `.env` tidak ter-track | ✅ aman | ✅ tidak ada API key hardcoded |

**Rincian P3-2.** Penting dibedakan: 2 lokasi memang menelan error, 2 lokasi
lain adalah import opsional yang sah — keduanya kini berjejak:

| Lokasi | Sifat | Penanganan |
|---|---|---|
| `rss_collector.py:101` | **bukan** penelanan — pola coba-format-tanggal-berikutnya | `logger.debug` |
| `client.py:123` | benar-benar menelan error body HTTP | `logger.debug(..., exc_info=True)` |
| `registry.py:90` | import `dotenv` opsional | `logger.debug` |
| `eulerpool.py:54` | import `dotenv` opsional | `logger.debug` |

Alasan `debug` dan bukan `warning`: keempatnya jalur normal, bukan kegagalan.
Yang diperbaiki adalah **tidak adanya jejak**, bukan level log-nya.

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
| **P1-1** | Vendor bobot via LFS / fetch ber-checksum | Sedang | Inferensi offline | ✅ |
| **P1-2** | Lock file + batas `numpy<3` | Kecil | Mencegah bug dependency | ✅ |
| **P1-3** | Samakan Python dev/CI | Kecil | Gerbang mutu bisa dijalankan lokal | ✅ |
| **P1-4** | Smoke test model nyata | Kecil | Menangkap "fallback diam-diam" | ✅ |
| **P1-5** | Uji metrik XAU (ECE/McNemar/bootstrap) | Sedang | Angka evaluasi terverifikasi | ✅ (59 baris I/O ⬜) |
| **P1-6** | `conftest.py` bersama | Kecil | Mengurangi duplikasi | ✅ |
| **P2-1** | Auth/rate limit API | Kecil | Keamanan saat dipublikasikan | ⬜ |
| **P2-2** | Test kolektor API berbayar | Sedang | Kuota & parsing error | ⬜ |
| **P2-3** | Hapus duplikasi `compute_mcnemar_test` / `compute_bootstrap_ci` | Kecil | Satu sumber kebenaran metrik | ✅ |
| **P2-4** | Perbarui `AGENTS.md` | Kecil | Info basi berbiaya tinggi | ✅ |
| **P2-5** | Keluarkan `.graphify/` dari git atau beri batas ukuran | Kecil | Repo membengkak, diff berisik | ⬜ |
| **P2-6** | Isolasi test `test_protokol_terpenuhi` dari VRAM | Kecil | Test gagal karena lingkungan, bukan logika | ✅ |
| **P3-1** | `datetime.utcnow()` deprecated | Kecil | Peringatan deprecation Python 3.12+ | ✅ |
| **P3-2** | `except: pass` tanpa jejak | Kecil | Error hilang tanpa log | ✅ |
| **P3-3** | Tidak ada TODO/FIXME | — | Observasi, bukan cacat | n/a |
| **P3-4** | `dataset/` + `research/papers/` di-track | Kecil | Repo membengkak | ⬜ |
| **P3-5** | Tidak ada migrasi/seed DB | Sedang | Skema tanpa jalur upgrade | ✅ |
| **P3-6** | Secret tidak ter-track | — | ✅ aman, tidak perlu tindakan | ✅ |

**Urutan pengerjaan P1** (dari yang paling murah dan berdampak) — ✅ **selesai dijalankan**:

1. **P1-2 + P1-3** — satu paket, keduanya soal dependency/Python. Menutup
   penyebab mypy merah di lokal sekaligus menutup celah `numpy 2.x`. ✅
2. **P1-4** — smoke test yang memastikan RoBERTa benar-benar dipakai, bukan
   fallback diam-diam. Ini yang paling berbahaya karena kegagalannya senyap. ✅
3. **P1-1** — vendor bobot atau fetch ber-checksum; bergantung keputusan Anda
   soal ukuran repo (bentrok dengan P2-5). ✅ Dipilih fetch ber-checksum
   (`scripts/fetch_weights.py`), LFS tidak dipakai — jadi tidak bentrok
   dengan P2-5.
4. **P1-6** lalu **P1-5** — `conftest.py` dulu agar helper uji metrik tidak
   terduplikasi saat menulis test baru. ✅ Keduanya selesai: P1-6 memindahkan
   fixture bersama, P1-5 memusatkan metrik (termasuk McNemar & bootstrap) di
   `model/common/metrics.py` dan menguji angka laporan XAU.

**Sisa kecil yang bukan P1:** 59 baris I/O `evaluate.py` (pemuatan model, loop
inferensi, `main()`) perlu uji integrasi bertanda `slow` bila ingin ditutup —
butuh bobot 440 MB di mesin uji. Duplikasi konseptual `compute_multiclass_ece`
dengan `model/common/metrics.py` masuk lingkup P2-3.


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

---

# Bagian II — Audit v2 (Delta)

**Tanggal:** 2026-10-28
**Commit yang diaudit:** `406cc3e` (`main`, merge PR #29)
**Basis pembanding:** Bagian I di atas, pada `b9550b3`
**Sifat:** **delta**, bukan audit ulang. Bagian I tetap berlaku apa adanya.

## II.0 Ringkasan

Sejak Bagian I ditulis, `main` menerima **45 commit** (`b9550b3..406cc3e`,
termasuk PR #28 dan #29) yang menambah tiga kontrak baru: preload berita
07:00 WIB, `POST /api/simulate`, dan penghapusan seluruh data karangan di GUI.

> **Cara membaca:** Bagian II hanya memuat **temuan baru** dan **status yang
> berubah**. Temuan Bagian I yang tidak disinggung berarti *tidak berubah* —
> jangan dibaca sebagai "sudah beres".

| Tingkat | Jumlah | Item |
|---|---|---|
| **P0** | 2 | `target` bebas · `SCHEMA.md` tertinggal |
| **P1** | 3 | simulate tanpa jejak · scheduler multi-proses · muat model 3,33 s |
| **P2** | 3 | batas panjang ganda · state instance · routing gagal jadi "netral" |
| **P3** | 2 | komentar "440 MB" · `MIN_CHARS=40` |
| **Sudah diperbaiki** | 1 | urutan News `published_at` (belum di-commit) |

**Kesimpulan satu paragraf.** Tiga kontrak baru itu **secara desain lebih jujur**
daripada yang digantikan: data karangan dibuang, gerbang masukan menolak
obrolan, dan satu model tidak lagi dipakai untuk dua ruang skor yang berlawanan
arah. Tetapi pintu masuknya belum dijaga seketat pintu lain — `target` menerima
string bebas — dan dokumen kontrak tertinggal satu rilis. Tidak ada temuan yang
menunjukkan jalur lama menghasilkan angka salah diam-diam.

## II.1 Lingkup & metode

**Di luar lingkup, disepakati dengan pemilik repo:**

| Area | Alasan |
|---|---|
| CI, `ruff`, `mypy` | sedang ditangani rekan lain — lihat §II.8 untuk serah-terima |
| `frontend/` | sedang disanitasi rekan lain — tidak disentuh sama sekali |
| `model/` | bobot tidak berubah di rentang commit ini |

**Diperiksa langsung:** `serve/app.py`, `serve/ingest_scheduler.py`,
`serve/news_preload.py`, `serve/sim_input.py`, `serve/sim_service.py`,
`store/db.py`, `context/SCHEMA.md`, `context/PRD.md`, `pyproject.toml`,
`Dockerfile`.

**Diukur, bukan diperkirakan:**

| Yang diukur | Hasil |
|---|---|
| `analyze()` panggilan pertama | **3,33 s** (muat bobot) |
| `analyze()` panggilan kedua | **0,016 s** |
| `analyze(target="BANANA")` | **diterima**, `direction="netral"`, `warnings=[]` |
| `analyze(target="")` | **diterima** |
| `analyze(target="xau")` vs `"XAU"` | sama (`bullish`) — pencocokan case-insensitive sudah benar |
| `Dockerfile` CMD uvicorn | tanpa `--workers` → 1 proses (P1-8 laten) |
| tabel `db.py` vs `SCHEMA.md` | 2 hilang: `ingest_runs`, `source_health` |

## II.2 Temuan P0

### P0-4 — `target` di `/api/simulate` menerima string bebas

`SimulateRequest.target` hanya `str` dengan batas panjang:

```python
target: str = Field(default="XAU", max_length=20)   # app.py:36
```

Tidak ada validasi terhadap tiga aset terkunci. Endpoint lain **sudah benar** —
`/api/series/{target}` memanggil `db.is_valid_target()` dan mengembalikan 404
(`app.py:210`).

```
target='BANANA'  → tone=positive  skor=0.993  direction=netral  warnings=[]
target=''        → tone=positive  skor=0.993  warnings=[]
```

**Mengapa P0.** Pengguna mengirim `"GOLD"` (nama wajar, bukan alias resmi).
Sistem tidak menolak; ia mengembalikan `direction="netral"` plus lima stance
persona yang tetap tampil meyakinkan. Pengguna membaca "netral" sebagai **hasil
analisis**, padahal artinya **target tidak dikenali**. Ini kelas kesalahan yang
sama dengan yang dihapus PR #28: kegagalan yang menyamar sebagai jawaban.

Bandingkan disiplin di tempat lain — `kind` sengaja tanpa nilai bawaan
(`app.py:28-30`) justru agar tidak ada penebakan. `target` jauh lebih longgar.

**Perbaikan.** `Literal["XAU","RATE_UST","SPX"]` atau `db.is_valid_target`,
tolak **422** dengan menyebut aset yang dikenali. Pertahankan normalisasi
huruf besar/kecil (sudah bekerja). Tes: target di luar tiga aset → 422.

### P0-5 — `SCHEMA.md` tidak mencatat tabel `ingest_runs` dan `source_health`

> **Koreksi (2026-10-28):** versi pertama temuan ini menyebut tabel
> `gui_preload_status`. **Nama itu tidak ada di kode** — saya salah membacanya.
> Tabel yang sebenarnya adalah `ingest_runs` dan `source_health`, dan masalahnya
> **dua tabel**, bukan satu. Klaim intinya tetap berdiri; rinciannya diperbaiki
> setelah diverifikasi ulang per tabel.

Kedua tabel ada di `db.py` dan dipakai untuk provenance serta alert, tetapi
`SCHEMA.md` tidak menyebutnya sama sekali. Diperiksa satu per satu terhadap
16 tabel di `db.py`:

```
HILANG   ingest_runs
HILANG   source_health
ADA      alloc_profiles, alloc_suggestions, articles, article_targets,
         asset_aliases, asset_master, daily_sentiment, impacts, labels,
         persona_views, prices, raw_articles, sentiments, stat_results
```

`SCHEMA.md:3` mewajibkan: *"Ubah skema → naikkan `schema_version` + catat
Changelog."* `schema_version` masih `0.7.0`, dan tidak satu pun berkas
`context/` diperbarui di PR #28/#29 (`git diff --name-only` hanya menunjukkan
penghapusan `context/AUDIT.md`).

**Dampak.** Siapa pun yang membangun ulang DB dari `SCHEMA.md` kehilangan
`ingest_runs` — lalu `has_run_for_slot` gagal, sehingga scheduler tidak bisa
membedakan "slot ini sudah ditarik" dari "belum", dan setiap restart aplikasi
mengulang tarikan serta membakar kuota harian eulerpool. `source_health` yang
hilang membuat query alert dan `consecutive_failures` tidak punya sumber.
RULES menetapkan dokumen yang menang saat konflik, jadi ini kontrak yang
dilanggar oleh kode — bukan cacat kosmetik.

**Perbaikan.** ✅ **SELESAI** — DDL kedua tabel ditambahkan di `SCHEMA.md` §6.1
(persis sesuai kode), `schema_version` dinaikkan ke `0.8.0`, Changelog diisi.
Sisa yang belum: `POST /api/simulate` belum tercatat di `PRD.md` /
`ARCHITECTURE.md`.

## II.3 Temuan P1

### P1-7 — `/api/simulate` tidak menyimpan hasil

```python
hasil = sim_service.analyze(...)   # app.py:369
return { ... }                      # tanpa db.save_*
```

Bandingkan `/api/persona/{article_id}` yang **memang** menyimpan — dengan
komentar `# S-2: persist supaya reproducible & bisa diperiksa ulang.`
(`app.py:354`).

**Dampak.** Teks yang dianalisis, model yang terpilih, dan skor yang dihasilkan
hanya hidup selama request. Kalau pengguna melaporkan "kemarin hasilnya
bullish", tidak ada cara memeriksa ulang — bahkan tidak bisa membuktikan teks
masukannya sama. Ini melemahkan prinsip *Explainable* (`DESIGN.md` §1) tepat di
halaman yang paling menonjol.

Bukan regresi (persona memang lebih dulu punya persistensi), tetapi rilis ini
menjadikan auditabilitas sebagai tema, jadi ketiadaan jejak ini menonjol.

**Perbaikan.** Simpan `(hash teks, kind, source, target, model_version, skor,
confidence, created_at)` — hash saja, bukan teks penuh, agar tidak menyimpan
data pengguna mentah. Tambah `GET /api/simulate/{id}`.

### P1-8 — Penjadwal preload mengandalkan asumsi satu proses

`lifespan` menyalakan scheduler di **setiap** proses (`app.py:105-108`). Tidak
ada kunci berbasis berkas/DB untuk mencegah dua proses menembak job yang sama.
Hari ini aman karena `Dockerfile:45` tidak memakai `--workers`.

**Jadi laten, bukan aktif.** Risikonya muncul begitu ada yang menambah
`--workers 4` atau menjalankan dua replika: beberapa proses menembak eulerpool
bersamaan dan membakar kuota — persis kekhawatiran yang sudah ditulis sendiri
di komentar `app.py:89-91` untuk kasus `--reload`, tetapi tidak dijaga untuk
kasus multi-worker.

**Perbaikan.** Kunci di level DB sudah cukup karena `ingest_runs` menyimpan
`scheduled_for` (unik per slot), sehingga `INSERT ... ON CONFLICT DO NOTHING`
dapat mencegah dua proses mengklaim slot yang sama. Alternatif: berkas kunci
di direktori data. Tambahkan catatan di README bahwa worker tunggal adalah
syarat, agar asumsinya tidak implisit.

### P1-9 — Model dimuat 3,33 s di dalam request pertama

```
panggilan pertama : 3,33 s
panggilan kedua   : 0,016 s
```

`SimulationService` sengaja satu instance per aplikasi (`app.py:119-120`) dan
pemuatan bersifat lazy. Akibatnya pengguna pertama setelah server hidup menunggu
~3,3 detik tanpa indikasi apa pun — tidak ada pembeda antara "sedang memuat
model" dan "server menggantung".

**Perbaikan.** Pilih satu: (a) panaskan model di `lifespan` sebelum `yield`,
(b) kembalikan 503 + `Retry-After` bila belum siap, atau (c) tampilkan status
"menyiapkan model" di GUI. Opsi (a) paling murah; konsekuensinya start lebih
lama, yang bisa diterima karena start jarang.

## II.4 Temuan P2 / P3

### P2-7 — Batas panjang ganda yang menyesatkan

`SimulateRequest.text` menerima **20.000** karakter, lalu `sim_input.validate`
menolak di atas **4.000** (`MAX_CHARS`). Fungsional benar (pesan 422 ramah),
tetapi pembaca skema OpenAPI akan mengira 20.000 boleh. Samakan.

### P2-8 — `_degraded` / `_score_space` disimpan sebagai state instance

`analyze()` menulis `self._degraded` dan `self._score_space` (`sim_service.py:277-278`),
lalu membacanya di akhir fungsi yang sama. Aman untuk satu request, tetapi
`SimulationService` adalah objek **bersama** antar request. Rute `def` (sinkron →
threadpool) membuat ini tidak aktif hari ini; nilainya sebagai jebakan refactor
bila kelak dijadikan `async def` atau dipanggil paralel di event loop yang sama.

### P2-9 — Routing gagal menghasilkan nilai yang identik dengan "netral"

```python
except Exception as exc:   # pragma: no cover - routing opsional
    logger.warning("Routing target gagal: %s", exc)      # sim_service.py:329
```

Bila `TargetRouter` gagal, `arah` tetap `"netral"` — **sama persis** dengan
"target tidak menyebut aset apa pun". Pengguna tidak bisa membedakan "memang
netral" dari "routing rusak". Pola yang sama dengan P0-4 dalam bentuk lebih
kecil. Minimal: `self._degraded.append("routing gagal: ...")` agar muncul di
`warnings`.

### P3-1 — Komentar "440 MB" mencampur dua model berbeda

`app.py:119-120` menyebut "bobot 440 MB". Pada pengukuran, model yang terpilih
untuk teks uji adalah `xau-finbert-20261025` dengan muat pertama 3,33 s. Angka
440 MB mungkin benar untuk FOMC-RoBERTa, tetapi mencampurnya dalam satu komentar
membuat pembaca salah memperkirakan biaya. Sebutkan per model.

### P3-2 — `MIN_CHARS=40` menolak judul berita pendek yang sah

Teks 37 karakter ditolak: *"Teks terlalu pendek (37 karakter, minimal 40)."*
Untuk mencegah "halo" itu masuk akal, tetapi judul finansial yang padat sering
di bawah 40 karakter (mis. `"Gold hits record high"` = 22). Ambang ini perlu
diuji terhadap judul nyata di `dataset/`, bukan angka bulat.

## II.5 Sudah diperbaiki di sesi ini — **belum di-commit**

### FIX-1 — News di Market Overview tidak urut tanggal terbit

**Gejala yang dilaporkan:** daftar News di halaman Market Overview tidak
tersortir berdasarkan tanggal terbaru.

**Akar masalah:** dua query memakai `ORDER BY created_at DESC` —
`query_impacts` (`db.py:1041`) dan `query_impact_time_audit` (`db.py:1101`).
`created_at` adalah waktu baris **ditulis** (kapan pipeline jalan), bukan waktu
terbit. Saat backlog di-ingest sekaligus, seluruh berita memperoleh
`created_at` nyaris sama, sehingga urutannya menjadi urutan ingest.

**Bukti dari data nyata (`data/finews.db`):**

```
pub=2026-10-20T09:11  cre=2026-10-28T03:01:25   ← tampil paling atas
pub=2026-10-20T16:27  cre=2026-10-28T03:01:24
pub=2026-10-20T10:37  cre=2026-10-28T03:01:24
```

Semua berita 20 Oktober di-ingest 28 Oktober pukul 03:01. `published_at` tidak
menurun pada urutan API (`False`).

**Perbaikan:** `ORDER BY a.published_at DESC, i.created_at DESC` pada kedua
query. `published_at` NULL (sumber tanpa tanggal) otomatis jatuh ke bawah karena
SQLite menganggap NULL lebih kecil dari nilai apa pun; `created_at` tetap dipakai
sebagai pemecah seri agar urutan deterministik.

**Verifikasi:** ketiga aset menurun benar dengan NULL di akhir —

```
XAU: True | RATE_UST: True | SPX: True
```

**Tes regresi** ditambahkan di `test_router_db_integration.py`. Tes ini
**dibuktikan menangkap bug**: saat bug lama dikembalikan sementara, tes
**gagal**; setelah dipulihkan, **lolos**. Bukan tes yang lolos kebetulan.

**Catatan:** `frontend/` tidak disentuh. `overview.js` merender apa pun yang
dikirim API, jadi perbaikan query langsung terlihat tanpa perubahan JS.

**Status: bekerja di branch `perfected`, belum di-commit** (menunggu
persetujuan pemilik repo).

## II.6 Prioritas perbaikan (Bagian II)

| ID | Temuan | Tingkat | Usaha | Status |
|---|---|---|---|---|
| P0-4 | `target` bebas di `/api/simulate` | P0 | S | ✅ selesai |
| P0-5 | `ingest_runs` + `source_health` tak tercatat di `SCHEMA.md` | P0 | S | ✅ selesai |
| P1-7 | `/api/simulate` tanpa jejak | P1 | M | ✅ selesai (0b53ca6) |
| P1-8 | Scheduler tanpa kunci multi-proses | P1 | M | ✅ selesai (6b50805) |
| P1-9 | Muat model 3,33 s di request pertama | P1 | S | ✅ selesai (a2234a4) |
| P2-7 | Batas 20.000 vs 4.000 | P2 | S | ✅ selesai (a732438) |
| P2-8 | State instance `_degraded` | P2 | S | ✅ selesai (a732438) |
| P2-9 | Routing gagal menyamar sebagai netral | P2 | S | ✅ selesai (a732438) |
| P3-1 | Komentar "440 MB" | P3 | XS | ✅ selesai (a732438) |
| P3-2 | `MIN_CHARS=40` vs judul pendek | P3 | S | ✅ selesai (a732438) |
| FIX-1 | Urutan News `published_at` | — | S | ✅ selesai (489a7bd) |

**Urutan yang disarankan:** P0-4 → P0-5 → P1-9 → P1-7 → P2-9 → sisanya.

Alasannya: P0-4 dan P0-5 sama-sama murah dan menutup celah "kegagalan menyamar
sebagai hasil". P1-9 sesudahnya karena murni pengalaman pengguna. P1-7 paling
mahal (perlu desain penyimpanan) sehingga ditaruh setelah itu. P2-9 murah dan
satu keluarga dengan P0-4.

## II.7 Yang sudah baik — jangan diubah

1. **Gerbang masukan `sim_input.py`** menolak obrolan dan pertanyaan **sebelum**
   memeriksa panjang, dengan alasan yang ditulis di komentar. Disiplin yang tepat.
2. **`kind` tanpa nilai bawaan** — mencegah pertanyaan diam-diam dianggap berita.
3. **`_pilih_model` memilih model per teks**, dengan penjelasan mengapa satu
   model untuk dua ruang skor membalik arah sinyal. Ini perbaikan yang benar dan
   alasannya didokumentasikan di kode.
4. **Penghapusan `demoImpacts`/`demoSeries`/`demoQuality`** — kegagalan API tidak
   lagi berubah menjadi berita contoh yang meyakinkan. Ini kelas perbaikan
   integritas yang paling berdampak di seluruh rilis.
5. **`has_run_for_slot` sengaja tidak menghitung `failed`/`partial`** agar
   kegagalan bisa dicoba ulang, sementara `ok`/`no_new` mencegah tarikan ganda
   saat restart. Pembedaan yang tepat.
6. **`api.js` meneruskan payload galat** sehingga `422` "itu sapaan, bukan
   berita" sampai ke pengguna, tidak tertelan menjadi "HTTP 422".
7. **Scheduler memakai clock yang bisa disuntik** (`clock=`), sehingga tes
   penjadwalan tidak perlu menunggu jam sungguhan.

## II.8 Serah-terima ke rekan (CI) — di luar lingkup saya

`main` saat ini **merah**. Dikonfirmasi lewat `gh run list`: run
`Merge pull request #29` berakhir `failure`, langkah **"Lint with ruff"**.
Docker build di-skip karena bergantung pada job itu.

`ruff check .` di lokal (ruff 0.17.0) menemukan **10 error**, semuanya mekanis:

| Berkas | Kode | Masalah |
|---|---|---|
| `serve/app.py:3` | I001 | import tak terurut |
| `serve/ingest_scheduler.py:35` | F401 | `datetime.time` tak terpakai |
| `serve/sim_service.py:108` | F841 | variabel `arah` tak terpakai |
| `serve/sim_service.py:318` | F841 | variabel `conf_router` tak terpakai |
| `test_ingest_scheduler.py:10` | F401 | `timedelta` tak terpakai |
| `test_ingest_scheduler.py:12` | F401 | `pytest` tak terpakai |
| `test_news_preload.py:34,65` | I001 | import tak terurut (2×) |
| `test_sim_input.py:177` | I001 | import tak terurut |
| `test_sim_service.py:100` | F841 | variabel `berita` tak terpakai |

Tujuh di antaranya bisa diperbaiki otomatis dengan `ruff check . --fix`. Tidak
saya sentuh karena CI milik rekan Anda.

**Catatan tambahan untuk beliau:** `test_sim_api.py` (8 tes) dan tiga berkas
lain bertanda `slow`, sehingga **tidak berjalan di CI** — `pyproject.toml`
menetapkan `addopts = "-ra -q -m 'not slow and not network'"` dan `ci.yml`
hanya menjalankan `pytest` polos. Kontrak HTTP `/api/simulate` (status 422,
bentuk payload galat, `degraded` sebagai list) karenanya tidak dijaga mesin.
Menjalankannya murah: model baseline TF-IDF sudah dilatih di `ci.yml:108`.

## II.9 Bukti mentah

```bash
# P0-4: target bebas diterima
PYTHONPATH=. ./venv/bin/python -c "
from backend.src.serve.sim_service import SimulationService
s=SimulationService(db_path='data/finews.db')
a='Gold surged 3.2% to a record high as the dollar collapsed and investors rushed into bullion as a safe haven.'
r=s.analyze(text=a,kind='berita',target='BANANA')
print(r.target, r.direction, r.warnings)"

# P0-5: tabel tak tercatat di dokumen
# P0-5: tabel yang hilang dari dokumen
for t in $(grep -oE "CREATE TABLE IF NOT EXISTS [a-z_]+" backend/src/store/db.py | sed "s/.*EXISTS //"); do
  grep -q "\b$t\b" context/SCHEMA.md || echo "HILANG $t"
done   # → HILANG ingest_runs / HILANG source_health

# P1-8: satu proses
grep -n "uvicorn" Dockerfile                        # → tanpa --workers

# P2-7: batas ganda
grep -n "max_length=20000" backend/src/serve/app.py
grep -n "MAX_CHARS" backend/src/serve/sim_input.py

# FIX-1: urutan setelah perbaikan
./venv/bin/python -m pytest backend/tests/test_router_db_integration.py -v
```

## II.10 Catatan metodologi

- Semua klaim diukur dengan menjalankan perintah; tidak ada yang diambil dari
  dokumentasi tanpa verifikasi.
- Temuan Bagian I **tidak** diverifikasi ulang. Statusnya tetap seperti tertulis
  di §6 Bagian I sampai ada audit khusus untuk itu.
- Angka 3,33 s berasal dari mesin pengembangan ini (model XAU). Mesin dengan
  model lebih besar akan berbeda; yang diklaim adalah **urutannya** — muat
  pertama jauh lebih mahal daripada panggilan berikutnya.
- Bagian II tidak mengubah kode kecuali FIX-1, yang masih di working tree dan
  belum di-commit.
