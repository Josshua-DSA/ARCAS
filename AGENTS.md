# AGENTS.md — Panduan untuk AI Agent Kolaborator

> Baca file ini dulu. Jangan membaca seluruh repository dari nol.
> Ada code graph yang sudah jadi — pakai itu untuk navigasi.

---

## 1. Mulai dari sini, bukan dari `ls -R`

Repository ini punya **code graph** yang sudah dibangun (`graphify-out/`).
Query jauh lebih murah daripada membaca puluhan file.

```bash
# Ringkasan arsitektur + daftar komunitas
cat graphify-out/GRAPH_REPORT.md

# Cari simbol dan lihat tetangganya (import, caller, method)
graphify explain "ModelRouter"
graphify explain "Database"

# Jalur antar dua simbol
graphify path "ModelRouter" "TargetImpact"

# Bangun ulang setelah kode berubah (gratis, tanpa API)
graphify update .
```

Buka `graphify-out/graph.html` di browser kalau butuh visual interaktif.

**Graph ini portabel** — tidak ada path absolut di dalamnya, jadi hasilnya sama
di mesin Anda.

---

## 2. Peta cepat: di mana apa

| Kalau Anda mencari… | Buka |
|---|---|
| Kontrak data (Pydantic, enum) | `backend/src/schema.py` |
| Skema SQLite + semua query | `backend/src/store/db.py` |
| Routing berita → target aset | `backend/src/tagging/router.py` |
| Routing berita → model spesialis | `backend/src/tagging/model_router.py` |
| Konversi dataset mentah | `backend/src/normalize/adapters.py` |
| Agregasi harian | `backend/src/aggregate/daily.py` |
| Allocation Tilt (wajib total 100%) | `backend/src/alloc/engine.py` |
| Stance persona | `backend/src/persona/engine.py` |
| Ekonometrika (Spearman/OLS-HAC/CAR/BH-FDR) | `backend/src/stats/engine.py` |
| REST API | `backend/src/serve/app.py` |
| Baseline ML (TF-IDF + LR) | `model/common/baseline.py` |
| Kontrak model inferensi | `model/common/protocol.py` |
| Metrik evaluasi (F1/ECE/kappa) | `model/common/metrics.py` |
| Track XAU (FinBERT-EMAS) | `model/xau/` |
| Track FOMC (RoBERTa) | `model/fomc/` |
| Konfigurasi router | `data/router_config.yaml` |

---

## 3. Aturan yang tidak boleh dilanggar

Ini bukan preferensi gaya — ini batasan arsitektur yang diuji.

1. **Universe terkunci: 3 target** — `XAU`, `RATE_UST`, `SPX`.
   Jangan menambah `OIL`, `CU`, `NG`, `BTC`, `USDIDR`, `DXY`, `VIX`, `IHSG`.
2. **Tanpa LLM generatif di jalur inferensi.** Model NLP hanya membaca teks dan
   mengeluarkan probabilitas 3-kelas. Semua agregasi, skor, dan statistik
   dihitung deterministik (pandas/scipy/statsmodels).
3. **Alokasi portofolio wajib 5 kelas** (`bond`, `mutual_fund`, `stock`, `etf`,
   `gold`) dengan total **tepat 100.0%**.
4. **Non-lookahead.** Model dibekukan; data baru hanya diinferensi. Tidak ada
   auto-retrain online. Cut-off harian UTC 00:00.
5. **`article_id` = SHA-256** dari teks yang sudah dinormalisasi. Jangan diganti.
6. **Hari tanpa berita = `NULL`/`NaN`**, bukan 0. Nol berarti "sentimen netral",
   yang berbeda maknanya.
7. **Jangan sentuh `frontend/`** kalau tugas Anda di jalur DB/Backend/ML.

---

## 4. Lingkup kerja per peran

| Peran | Direktori | Jangan sentuh |
|---|---|---|
| Database | `backend/src/store/` | `model/`, `frontend/` |
| Backend | `backend/src/`, `data/` | `model/`, `frontend/` |
| ML | `model/`, `backend/src/tagging/` | `frontend/` |
| Frontend | `frontend/` | `backend/`, `model/` |

---

## 5. Perintah yang sering dipakai

```bash
# Test — wajib hijau sebelum commit
./venv/bin/python -m pytest

# Lint
./venv/bin/python -m ruff check .

# Format + lint otomatis
./venv/bin/python -m ruff check . --fix

# Jalankan API
./venv/bin/python -m uvicorn backend.src.serve.app:create_app --factory --reload

# Bangun ulang bobot router (butuh dataset)
./venv/bin/python scripts/build_router_centroids.py

# Eksplorasi baseline ML
/home/josjiez/my_env/ai_env/bin/python model/common/01_baseline_exploration.py
```

Baseline: **25–31 test lulus** tergantung cabang. Kalau jumlahnya turun,
ada yang rusak.

---

## 6. Konvensi commit

Satu file = satu commit. Format:

```
type(scope): imperative lowercase description
```

`type` ∈ `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `data`, `ci`.
`scope` ∈ `backend`, `model`, `data`, `context`, `gui`, `frontend`, `research`, `dataset`.
Tambahkan `!` untuk breaking change (`refactor(model)!: ...`).

---

## 7. Kondisi repository saat ini

Yang **sudah** ada:
- Skema DB 14 tabel + migrasi idempoten
- Router dua tahap (source hint → log-odds Monroe 2008), akurasi ~95–98%
- Audit trail routing tersimpan di tabel `impacts`
- Baseline TF-IDF + LR, metrik F1/ECE/kappa
- REST API, Allocation Tilt, Persona POV, StatEngine

Yang **belum** ada (jangan diasumsikan ada):
- Implementasi FinBERT (`model/xau/src/` masih kosong)
- Implementasi FOMC-RoBERTa (`model/fomc/src/` masih kosong)
- Orchestrator pipeline end-to-end (collect → clean → route → score → save)
- CRUD untuk 8 tabel (`articles`, `article_targets`, `sentiments`, dll.)
- File database disk `data/finews.db` (belum pernah diinisialisasi)
- Kolektor berita (RSS/scraper) — baru ada kolektor harga yfinance

---

## 8. Saat ragu

Baca `context/PRD.md`, `context/RULES.md`, `context/SCHEMA.md`,
`context/ARCHITECTURE.md`, `context/DESIGN.md` — itu sumber kebenaran.
Kalau kode bertentangan dengan dokumen tersebut, **dokumen yang menang**,
dan kode yang harus diperbaiki.
