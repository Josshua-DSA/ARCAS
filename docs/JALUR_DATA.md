# Jalur Data — K-3 → A → C → B

Dokumen ini menjelaskan empat jalur data yang berjalan di repo ini, urutan
ketergantungannya, dan cara memverifikasi bahwa masing-masing benar-benar
mengambil data nyata (bukan simulasi).

Lingkup terkunci: **XAU, RATE_UST, SPX** — hanya tiga ini.

---

## Urutan jalur

```
K-3  CRUD tabel          →  fondasi: skema & penyimpanan
 A   Harga                →  butuh tabel `prices`
 C   Berita via API       →  butuh tabel `raw_articles`/`articles`
 B   Berita via RSS       →  pelengkap C, menutup celah cakupan
```

Urutan ini disengaja: K-3 harus ada lebih dulu karena A, C, dan B semuanya
menulis ke tabel. C dijalankan sebelum B karena API memberi metadata
terstruktur (sentimen vendor, entitas), sedangkan RSS menutup sumber yang
tidak terindeks API.

---

## K-3 — CRUD tabel

Modul: `backend/src/store/db.py` (method baru), skema di `DDL_SCHEMA`.

| Tabel | Fungsi | Method utama |
|---|---|---|
| `raw_articles` | berita mentah dari API/RSS | `save_raw_article`, `save_raw_articles`, `query_raw_articles`, `count_raw_articles` |
| `articles` | berita ternormalisasi (`article_id`) | `save_article`, `save_articles`, `get_article`, `article_exists`, `query_articles`, `count_articles` |
| `article_targets` | pemetaan berita → target | `save_article_target`, `save_article_targets`, `query_article_targets`, `query_articles_by_target` |
| `sentiments` | keluaran model per artikel | `save_sentiment`, `query_sentiments` |
| `labels` | anotasi manusia (Cohen's kappa) | `save_label`, `save_labels`, `query_labels`, `count_labels` |

Catatan penting:

- **Dedup `raw_articles`** memakai `(source, url)` bila URL ada, selain itu
  `(source, title)`. Menjalankan ingest dua kali tidak menggandakan baris.
- `save_raw_articles` mengembalikan **jumlah baris baru**, bukan jumlah input —
  jadi bisa dipakai untuk memantau hasil ingest.
- `save_sentiment` menulis **satu baris per model** (primary key gabungan
  `article_id, model, model_version`), bukan satu baris per artikel.

---

## Jalur A — Harga

Modul: `backend/src/collect/yfinance_collector.py`

Sumber: **Yahoo Finance chart API** (`query1.finance.yahoo.com/v8/finance/chart`),
dipanggil lewat `urllib` stdlib. `yfinance` tidak dipakai.

Ticker: `XAU=GC=F`, `RATE_UST=^TNX`, `SPX=^GSPC`.

### Perubahan penting: fallback sintetis dihapus

Sebelumnya `fetch_prices` membungkus semuanya dalam `try/except Exception` dan
**diam-diam mengembalikan data acak** saat jaringan gagal. Itu berbahaya: pipeline
tampak sukses padahal isinya angka sintetis, dan hasil ekonometriknya tidak berarti.

Sekarang:

- `fetch_prices()` **melempar `PriceFetchError`** bila gagal — tidak ada fallback.
- `fetch_prices_synthetic()` masih ada, tetapi **hanya dipanggil eksplisit**
  (untuk test/offline). Namanya sengaja dibuat berbeda agar tidak bisa tertukar.
- `fetch_universe_prices()` mencatat kegagalan per aset di `last_errors`; satu
  aset gagal tidak menghentikan yang lain, tapi bila **semua** gagal ia melempar.
- `fetch_with_meta()` mengembalikan `FetchResult` dengan field `source` sehingga
  asal data (`yahoo` vs `synthetic`) selalu bisa diaudit.

Verifikasi:

```bash
python -c "
from datetime import date, timedelta
from backend.src.collect.yfinance_collector import PriceCollector
pc = PriceCollector()
end = date.today(); start = end - timedelta(days=7)
for a, r in pc.fetch_universe_prices(start, end).items():
    print(a, len(r), 'bar, close', r[-1].close)
"
```

---

## Jalur C — Berita via API

Paket: `backend/src/collect/news_api/`

```
base.py          kontrak: NewsItem, HealthReport, ApiStatus, LOCKED_TARGETS
client.py        HTTP GET + retry/backoff + klasifikasi error (tanpa bocor token)
keywords.py      pencocokan kata kunci target (word-boundary regex)
finnhub.py       adapter Finnhub
marketaux.py     adapter Marketaux
alphavantage.py  adapter Alpha Vantage
registry.py      identifikasi penyedia: env ada? kunci valid? ada data?
```

### Status kunci (terverifikasi 2026-10-21)

| Penyedia | Status | Catatan |
|---|---|---|
| **Finnhub** | `ok` | 100 item. Sumber utama berita. |
| **Marketaux** | `ok` | Perlu `countries=us`; `symbols=XAUUSD`/`GC=F` → 0 hasil di free tier. HTTP 500 = kuota harian habis. |
| **Alpha Vantage** | `premium_only` | `NEWS_SENTIMENT` butuh langganan; dilaporkan sebagai `premium_only`, bukan "tidak ada berita". |

Status bukan biner: `ok`, `empty`, `no_key`, `unauthorized`, `rate_limited`,
`premium_only`, `error`. Adapter tidak pernah melempar ke pemanggil saat
`probe()` — kegagalan jadi laporan, bukan crash.

### Relevansi: bug yang diperbaiki

Pencocokan kata kunci awalnya memakai substring biasa. Akibatnya kata kunci
`"war"` cocok di dalam **"softwar"**, **"award"**, **"toward"**, **"hardware"** —
dan berita NBA lolos sebagai berita XAU. Sekarang:

- pencocokan memakai **word-boundary regex** (`(?<!\w)…(?!\w)`);
- frasa cocok lintas spasi/hyphen (`safe haven` = `safe-haven`);
- kata kunci **makro saja tidak cukup** — `matches_target` mewajibkan minimal
  satu kata kunci target-spesifik, jadi "Inflation eased" tidak lolos ke XAU;
- hasil diurutkan `score_relevance` (kata kunci target berbobot 2x makro).

### Identifikasi API

```bash
python -m backend.src.collect.news_cli identify   # tabel status + feed RSS
python -m backend.src.collect.news_cli health --json
```

---

## Jalur B — Berita via RSS

Modul: `backend/src/collect/rss_collector.py`

Parser RSS 2.0 + Atom memakai `xml.etree.ElementTree` (stdlib, tanpa `feedparser`).

### Feed terverifikasi hidup

| Feed | Target | Item |
|---|---|---|
| `investing_commodities_news` (`news_11.rss`) | XAU, RATE_UST | 10 |
| `investing_commodities_analysis` (`commodities.rss`) | XAU | 10 |
| `marketwatch_top` | XAU, SPX | 10 |
| `fed_press` | RATE_UST | 20 |
| `bbc_business` | SPX | 52 |

### Feed yang dibuang (jangan dipakai lagi)

| Feed | Alasan |
|---|---|
| `kitco.com/rss/news.xml`, `KitcoNews.xml` | HTTP 404 |
| `feeds.finance.yahoo.com/rss/2.0/headline` | HTTP 404 (dipensiunkan) |
| `investing.com/rss/news_285.rss` | Hidup, **tapi isinya saham/bitcoin** — bukan komoditas |

Kesalahan `news_285` sempat membuat XAU mendapat **0 berita** meski feed
"sehat". Pelajarannya: status HTTP 200 tidak menjamin isi feed sesuai lingkup —
selalu periksa judul aktualnya.

---

## Menjalankan ingest

```bash
# tarik berita (API + RSS) untuk ketiga target, simpan ke DB
python -m backend.src.collect.news_cli fetch --target all --limit 20

# pratinjau tanpa menulis
python -m backend.src.collect.news_cli fetch --target XAU --dry-run

# hanya satu sumber
python -m backend.src.collect.news_cli fetch --target SPX --rss-only
python -m backend.src.collect.news_cli fetch --target SPX --api-only
```

Contoh keluaran (nyata, 2026-10-21): 38 berita baru tersimpan dari 38 kandidat;
run kedua menyimpan **0** karena dedup bekerja.

---

## Test

```bash
python -m pytest          # 62 passed
```

Cakupan baru: `test_news_api.py` (kata kunci, word-boundary, klasifikasi error,
adapter tanpa kunci) dan `test_news_crud.py` (CRUD kelima tabel + parsing RSS/Atom).

---

## Batasan yang perlu diketahui

1. **Marketaux free tier** hanya 100 req/hari dan bisa mengembalikan HTTP 500
   saat kuota habis — bukan bug kode, tapi kuota.
2. **Alpha Vantage** tidak berguna untuk berita pada paket gratis.
3. **RATE_UST** mendapat berita lebih sedikit karena `^TNX` adalah indeks yield;
   sumber berita langsung tentang yield terbatas pada siaran Fed dan komoditas.
4. **Yahoo chart API** tidak resmi untuk penggunaan produksi; bila diblokir,
   `fetch_prices` akan melempar error (bukan mengarang data).
5. Relevansi berbasis kata kunci masih bisa salah pada berita ambigu; ini
   tahap penyaring awal, bukan klasifikasi final.
