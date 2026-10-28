# SCHEMA — Data Contracts

> Sumber kebenaran struktur data. Ubah skema → naikkan `schema_version` + catat Changelog.
> `schema_version: 0.8.0`

## 1. Enum

```python
from enum import Enum

class Tone(str, Enum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"

class Direction(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    MIXED = "mixed"

class AssetClass(str, Enum):
    COMMODITY = "commodity"   # XAU
    INDEX = "index"           # SPX
    RATE = "rate"             # RATE_UST

class Track(str, Enum):
    A_IDX = "A"   # MATI 2026-10-11 (dataset ID dihapus)
    B_GLOBAL = "B"   # AKTIF: gold + FOMC

class Basis(str, Enum):
    EXPLICIT = "explicit"
    MACRO_FACTOR = "macro_factor"
    SECTOR_INFERRED = "sector_inferred"   # DICORET MVP, jangan pakai

class Lang(str, Enum):
    ID = "id"
    EN = "en"
    OTHER = "other"
```

## 2. Model Pipeline (Pydantic v2)

```python
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field

class RawArticle(BaseModel):
    source: str                  # "cnbc_id", "kontan", "finnhub", "fed_rss", ...
    url: Optional[str] = None
    title: str
    body: Optional[str] = None
    published_at: Optional[datetime] = None   # UTC
    fetched_at: datetime
    query_target: Optional[str] = None        # target yang memicu pengambilan (routing)
    vendor_sentiment: Optional[float] = None  # skor bawaan API (hanya pembanding)

class Article(BaseModel):
    article_id: str              # sha256(norm(title)+norm(body))[:16]
    source: str
    url: Optional[str]
    title: str
    body: Optional[str]
    language: Lang
    published_at: Optional[datetime]
    fetched_at: datetime
    effective_trading_date: dict[str, date]   # per target/bursa, mis. {"XAU":"2026-10-12"}
    duplicate_of: Optional[str] = None
    market_relevant: Optional[bool] = None

class TargetTag(BaseModel):
    asset_id: str                # kunci asset_master
    basis: Basis
    matched_text: Optional[str] = None
    span: Optional[tuple[int, int]] = None
    routed_from: Optional[str] = None   # "registry" | "alias" | "ner" | "macro"

class ModelProbs(BaseModel):
    model: str                   # "tfidf_lr" | "finbert" | "fomc_roberta" | "fusion" (indobert/finbert_mt mati 2026-10-11)
    p_pos: float; p_neu: float; p_neg: float
    model_version: str

class ArticleSentiment(BaseModel):
    article_id: str
    tone: Tone                   # dari model terpilih (mis. fusion)
    score: float = Field(ge=-1, le=1)   # p_pos - p_neg
    probs: list[ModelProbs]      # semua model (untuk ablation/audit)
    translation_used: bool = False
    translator_version: Optional[str] = None

class EvidenceSpan(BaseModel):
    quote: str = Field(max_length=300)   # substring persis dari title/body
    start: int
    end: int

class TargetImpact(BaseModel):
    article_id: str
    asset_id: str
    direction: Direction
    score: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)      # final, dihitung kode, terkalibrasi
    basis: Basis
    themes: list[str] = []
    causal_path: Optional[list[str]] = None    # ["rates_down","usd_down","gold_up"]
    rationale: Optional[str] = Field(default=None, max_length=500)
    evidence: list[EvidenceSpan] = []
    flags: list[str] = []                      # rumor, mixed_signal, ambiguous_entity, weak_source

class DailySentiment(BaseModel):
    asset_id: str
    date: date                                 # hari bursa efektif
    score_mean: Optional[float]                # None/NaN bila n_articles == 0
    score_weighted: Optional[float]
    n_articles: int
    n_sources: int
    has_news: bool
    version: str

class StatResult(BaseModel):
    run_id: str
    asset_id: str
    test: str            # pearson|spearman|ols|granger|event_study
    market_metric: str   # return|abnormal_return|volatility|volume_change
    lag: Optional[int]
    estimate: float
    ci_low: Optional[float]; ci_high: Optional[float]
    p_value: float
    p_adjusted: Optional[float]
    n_obs: int
    period_start: date; period_end: date
    params_json: str
    code_version: str
```

## 3. Output JSON (contoh)

```json
{
  "article_id": "a91f03c2d7b14e55",
  "language": "id",
  "sentiment": {
    "tone": "positive", "score": 0.71,
    "probs": [
      {"model": "indobert",   "p_pos": 0.78, "p_neu": 0.15, "p_neg": 0.07, "model_version": "indobert-ft-v1"},
      {"model": "finbert_mt", "p_pos": 0.66, "p_neu": 0.25, "p_neg": 0.09, "model_version": "finbert-prosus@mt-v1"},
      {"model": "fusion",     "p_pos": 0.80, "p_neu": 0.14, "p_neg": 0.06, "model_version": "stack-lr-v1"}
    ],
    "translation_used": true
  },
  "impacts": [
  {
    "asset_id": "XAU", "direction": "bullish", "score": 0.74, "confidence": 0.88,
    "basis": "explicit", "themes": [], "flags": [],
    "evidence": [{"quote": "Gold rises on rate-cut bets", "start": 0, "end": 27}]
  },
    {
      "asset_id": "XAU", "direction": "bullish", "score": 0.40, "confidence": 0.62,
      "basis": "macro_factor", "themes": ["rates_down"],
      "causal_path": ["rates_down", "gold_up"], "flags": []
    }
  ],
  "model_version": "fusion-v1", "universe_version": "2026-10-12-core3", "schema_version": "0.5.0",
  "disclaimer": "Bukan nasihat investasi."
}
```

## 4. Universe (`asset_master`)

| Kolom | Tipe | Keterangan |
|---|---|---|
| `asset_id` | str PK | Murni 3 v2026-10-11-p3: `XAU`, `RATE_UST`, `SPX` (7 dicoret 2026-10-11) |
| `asset_class` | enum | commodity/crypto/index/equity/fx |
| `track` | enum | A / B |
| `name` | str | Nama resmi |
| `price_ticker` | str | Ticker Yahoo terkunci (`GC=F`, `^TNX`, `^GSPC`) — verifikasi saat implementasi |
| `exchange` | str | IDX, NYSE, CME, … |
| `country` | str | ISO alpha-2 |
| `sector` | str | `NULL` untuk MVP makro (kolom cadangan) |
| `timezone` | str | mis. `Asia/Jakarta`, `America/New_York` |
| `session_close` | time | Jam tutup bursa/pasar (untuk time-align) |
| `valid_from` / `valid_to` | date | Point-in-time (universe v2026-10-12-core3; bump saat tambah/coret target) |
| `active` | bool | |

`aliases.csv`: `asset_id`, `alias`, `lang` (mis. "emas", "gold", "bullion" → `XAU`; "treasury yield", "10-year" → `RATE_UST`; "s&p 500", "sp500" → `SPX`). Tanpa alias emiten (dicoret MVP).

> XAU: konvensi `effective_trading_date` = cut-off harian 00:00 UTC di config, catat di `RULES.md`. RATE_UST/SPX ikut kalender US.

## 5. Source Registry & Impact Graph

Lihat `ARCHITECTURE.md` §4 (`data/source_registry.yaml`) dan `DESIGN.md` §4.2 (`data/impact_graph.yaml`).

## 6. Tabel Database (SQL)

```sql
CREATE TABLE raw_articles (
  raw_id INTEGER PRIMARY KEY, source TEXT, url TEXT, title TEXT, body TEXT,
  published_at TIMESTAMP, fetched_at TIMESTAMP, query_target TEXT, vendor_sentiment REAL,
  payload_json TEXT
);

CREATE TABLE articles (
  article_id TEXT PRIMARY KEY, source TEXT, url TEXT, title TEXT, body TEXT,
  language TEXT, published_at TIMESTAMP, fetched_at TIMESTAMP,
  duplicate_of TEXT, market_relevant BOOLEAN
);

CREATE TABLE article_targets (
  article_id TEXT REFERENCES articles(article_id),
  asset_id TEXT, basis TEXT, matched_text TEXT, routed_from TEXT,
  effective_trading_date DATE,
  PRIMARY KEY (article_id, asset_id)
);

CREATE TABLE sentiments (
  article_id TEXT REFERENCES articles(article_id),
  model TEXT, model_version TEXT,
  p_pos REAL, p_neu REAL, p_neg REAL,
  translation_used BOOLEAN, translator_version TEXT, created_at TIMESTAMP,
  PRIMARY KEY (article_id, model, model_version)
);

CREATE TABLE impacts (
  article_id TEXT, asset_id TEXT,
  direction TEXT, score REAL, confidence REAL, basis TEXT,
  themes_json TEXT, causal_path_json TEXT, rationale TEXT, evidence_json TEXT, flags_json TEXT,
  model_version TEXT, universe_version TEXT, schema_version TEXT, created_at TIMESTAMP,
  PRIMARY KEY (article_id, asset_id, model_version)
);

CREATE TABLE daily_sentiment (
  asset_id TEXT, date DATE, score_mean REAL, score_weighted REAL,
  n_articles INTEGER, n_sources INTEGER, has_news BOOLEAN, version TEXT,
  PRIMARY KEY (asset_id, date, version)
);

CREATE TABLE prices (
  asset_id TEXT, date DATE, open REAL, high REAL, low REAL, close REAL, adj_close REAL, volume REAL,
  PRIMARY KEY (asset_id, date)
);

CREATE TABLE stat_results (
  run_id TEXT, asset_id TEXT, test TEXT, market_metric TEXT, lag INTEGER,
  estimate REAL, ci_low REAL, ci_high REAL, p_value REAL, p_adjusted REAL,
  n_obs INTEGER, period_start DATE, period_end DATE, params_json TEXT, code_version TEXT
);

CREATE TABLE labels (
  article_id TEXT, asset_id TEXT, annotator TEXT, label TEXT, labeled_at TIMESTAMP,
  PRIMARY KEY (article_id, asset_id, annotator)
);

CREATE TABLE asset_master ( asset_id TEXT PRIMARY KEY, asset_class TEXT, track TEXT, name TEXT,
  price_ticker TEXT, exchange TEXT, country TEXT, sector TEXT, timezone TEXT, session_close TEXT,
  valid_from DATE, valid_to DATE, active BOOLEAN );
CREATE TABLE asset_aliases ( asset_id TEXT, alias TEXT, lang TEXT );

CREATE INDEX idx_impacts_asset ON impacts(asset_id, created_at);
CREATE INDEX idx_daily_asset_date ON daily_sentiment(asset_id, date);
```

Parquet dipakai untuk dump besar (`raw/`, `processed/`) dan dataset pelatihan.

### 6.1 Operasional Ingest & Kesehatan Sumber (v0.8.0)

Dua tabel ini ditambahkan bersama job preload berita 07:00 WIB, tetapi baru
dicatat di sini pada v0.8.0. Keduanya bersifat **operasional** — tidak menyentuh
skor atau analisis — namun wajib ada karena dipakai untuk provenance dan alert.

```sql
-- Jejak setiap tarikan berita terjadwal. Tujuannya:
--   1. GUI bisa menyatakan "data per <waktu>" saat API mati (tidak mengarang).
--   2. Job yang terlewat (aplikasi mati semalaman) bisa "mengejar" sekali saat
--      startup, lalu lanjut jadwal normal -- dibedakan lewat `trigger`.
CREATE TABLE ingest_runs (
  run_id INTEGER PRIMARY KEY AUTOINCREMENT,
  trigger TEXT NOT NULL,              -- 'schedule' | 'startup_catchup' | 'manual'
  status TEXT NOT NULL,               -- 'running' | 'ok' | 'partial' | 'failed'
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  scheduled_for TIMESTAMP,            -- slot 07:00 WIB yang diwakili run ini
  raw_new INTEGER NOT NULL DEFAULT 0,
  articles_clean INTEGER NOT NULL DEFAULT 0,
  impacts_new INTEGER NOT NULL DEFAULT 0,
  detail TEXT
);
CREATE INDEX idx_ingest_runs_finished ON ingest_runs(finished_at);

-- Riwayat kesehatan sumber. Satu baris per (sumber, pemeriksaan).
-- `is_failure` sengaja berupa kolom agar query alert tidak perlu mengulang
-- logika "status apa saja yang dianggap gagal" di banyak tempat.
CREATE TABLE source_health (
  source TEXT NOT NULL,
  checked_at TIMESTAMP NOT NULL,
  status TEXT NOT NULL,
  is_failure BOOLEAN NOT NULL DEFAULT 0,
  usable BOOLEAN NOT NULL DEFAULT 0,
  latency_ms REAL,
  detail TEXT,
  sample_size INTEGER NOT NULL DEFAULT 0,
  consecutive_failures INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_source_health_source ON source_health(source, checked_at);
```

**Invarian operasional:**

- `status` pada `ingest_runs` menentukan apakah slot boleh diulang. Hanya `ok`
  dan `no_new` yang dianggap "sudah membawa data"; `failed`/`partial` sengaja
  **tidak** dihitung supaya kegagalan tetap bisa dicoba ulang. Lihat
  `Database.has_run_for_slot`.
- `scheduled_for` adalah slot 07:00 WIB (Asia/Jakarta), bukan waktu UTC.
- `source_health` bersifat append-only per pemeriksaan; `consecutive_failures`
  adalah turunan yang dipakai untuk alert, bukan sumber kebenaran.

## 7. Invarian (wajib dijaga validator)

1. `asset_id` ∈ `asset_master` pada `universe_version` yang dipakai.
2. `p_pos + p_neu + p_neg ≈ 1` (toleransi 1e-3); `score = p_pos − p_neg`.
3. `direction` konsisten dengan `score`: bullish ⇒ score > +0.1; bearish ⇒ < −0.1; neutral ⇒ |score| ≤ 0.1; mixed ⇒ flag `mixed_signal`.
4. `basis=explicit` ⇒ `evidence ≥ 1` dan `quote` substring persis dari title/body.
5. `confidence` ≤ cap per `basis`.
6. `daily_sentiment`: `n_articles == 0` ⇒ `score_mean IS NULL` dan `has_news = false` (dilarang mengisi 0).
7. `effective_trading_date` harus hari bursa target (bukan akhir pekan/libur) kecuali target 24 jam sesuai konvensi.
8. Tidak ada kebocoran: fitur/skor untuk tanggal `t` hanya memakai berita dengan `published_at ≤ cut-off t`.
9. Tidak ada duplikasi `(article_id, asset_id, model_version)`.

## 8. Tambahan v0.3 — Allocation & Persona

```python
class AllocClass(str, Enum):
    BOND = "bond"
    MUTUAL_FUND = "mutual_fund"
    STOCK = "stock"
    ETF = "etf"
    GOLD = "gold"          # XAU direct
    CASH = "cash"          # opsional (BTC dicoret 2026-10-11)

class Stance(str, Enum):
    BUY = "buy"            # hijau
    HOLD = "hold"          # abu
    SELL = "sell"          # merah

class NewsHorizon(str, Enum):
    INTRADAY = "intraday"
    SHORT = "short"        # 1-5 hari
    MEDIUM = "medium"      # 1-4 minggu
    LONG = "long"          # > 1 bulan

# TargetImpact: tambahkan field
#   news_horizon: NewsHorizon

class ClassScore(BaseModel):
    alloc_class: AllocClass
    score: float = Field(ge=-1, le=1)
    confidence: float = Field(ge=0, le=1)
    sources: list[str]                    # asset_id/tema yang berkontribusi

class AllocationLine(BaseModel):
    alloc_class: AllocClass
    baseline_pct: float
    new_pct: float
    delta_pp: float
    confidence: float
    rationale: str = Field(max_length=300)
    no_change: bool = False

class AllocationSuggestion(BaseModel):
    article_id: str
    profile_id: str                       # "conservative" | "moderate" | "aggressive" | "custom:<id>"
    lines: list[AllocationLine]           # Σ new_pct == 100
    params_version: str
    created_at: datetime
    disclaimer: str = "Simulasi analitis. Bukan nasihat investasi."

class PersonaView(BaseModel):
    article_id: str
    persona_id: str                       # retail | day_trader | fund_manager | pension | risk_manager
    target: str                           # asset_id atau alloc_class
    stance: Stance
    strength: float = Field(ge=0, le=1)
    news_horizon: NewsHorizon
    raw_value: float
    confidence: float
    rationale: str = Field(max_length=300)
    params_version: str
    disclaimer: str = "Simulasi sudut pandang. Bukan nasihat investasi."
```

`asset_master.asset_class` ditambah nilai: `bond`, `mutual_fund`, `etf` (dengan `price_ticker`/NAV TBD).

```sql
CREATE TABLE alloc_profiles ( profile_id TEXT, alloc_class TEXT, base_pct REAL, min_pct REAL, max_pct REAL,
  PRIMARY KEY (profile_id, alloc_class) );
CREATE TABLE alloc_suggestions ( article_id TEXT, profile_id TEXT, alloc_class TEXT,
  baseline_pct REAL, new_pct REAL, delta_pp REAL, confidence REAL, rationale TEXT, no_change BOOLEAN,
  params_version TEXT, created_at TIMESTAMP, PRIMARY KEY (article_id, profile_id, alloc_class, params_version) );
CREATE TABLE persona_views ( article_id TEXT, persona_id TEXT, target TEXT, stance TEXT, strength REAL,
  news_horizon TEXT, raw_value REAL, confidence REAL, rationale TEXT, params_version TEXT, created_at TIMESTAMP,
  PRIMARY KEY (article_id, persona_id, target, params_version) );
```

**Invarian tambahan**
10. `Σ new_pct == 100.0` (toleransi 1e-6) dan `Σ base_pct == 100.0` untuk setiap profil; validasi saat memuat `alloc_profiles.yaml`.
11. `min_pct ≤ new_pct ≤ max_pct`; `|delta_pp| ≤ Δmax`.
12. `stance` konsisten dengan ambang persona (`raw_value`, `confidence`); monoton terhadap `score`.
13. Setiap `AllocationSuggestion`/`PersonaView` wajib memuat `disclaimer`.

## 8.1 Kontrak Role
ML → `ArticleSentiment {tone, score=p_pos-p_neg, probs[], translation_used}`. Backend → `TargetImpact {direction, score, confidence, basis, themes, causal_path, evidence, flags}` → `DailySentiment {score_mean NULL bila kosong}` → `StatResult {estimate, CI, p, p_adj, n_obs}` + `AllocationSuggestion {Σ100%}` + `PersonaView {BUY/HOLD/SELL}`. ML dilarang tulis direction/confidence/statistik. Backend dilarang ubah probabilitas.

## 9. Changelog

- 0.8.0-operasional — Catat dua tabel yang sudah ada di kode tetapi belum pernah didokumentasikan: `ingest_runs` (jejak tarikan terjadwal, dipakai `has_run_for_slot` untuk mencegah tarikan ganda saat restart) dan `source_health` (riwayat kesehatan sumber + `consecutive_failures` untuk alert). Keduanya operasional; tidak ada perubahan pada skor, enum, atau kontrak analisis. Ditemukan lewat audit v2 (P0-5).
- 0.7.0-core3 — Pin Tools: `STOCK`→`SPX`, `ETF`→`SPX`, kelas alokasi `BTC` dibekukan (`no_change`); seed nonaktifkan aset pensiun; tanpa perubahan struktur tabel (schema_version tetap 0.5.0).
- 0.7.0 — Supervised 3 (`XAU/RATE_UST/SPX`); Track A mati; `ModelProbs` tanpa indobert/finbert_mt; dataset gold+FOMC lokal.
- 0.6.1 — PhraseBank dihapus (bukan makro); `dataset/` kosong.
- 0.6.0 — Universe 11→10 (IHSG + `^JKSE` dicoret); dataset FNSPID/IHSG dihapus, sisa PhraseBank.
- 0.5.0 — Universe LOCKED 11 target (XAU/OIL/CU/NG/BTC/USDIDR/DXY/RATE_UST/VIX/IHSG/SPX); coret XAG/NDX/DJI/emiten/SBN-single-name; AssetClass +rate/+volatility, hapus equity; aliases kata kunci komoditas/makro.
- 0.4.0 — Hapus `llm_fewshot` dari `ModelProbs`; scope tanpa LLM/RAG/agent.

- 0.3.0 — Tambah `news_horizon`, `AllocationSuggestion`, `PersonaView`, kelas aset obligasi/reksadana/ETF.

- 0.2.0 — Skema ulang: dua track (IDX/Global), multi-model (`sentiments`), `daily_sentiment`, `stat_results`, `prices`, `source_registry`.
- 0.1.0 — Draf awal (cross-asset impact).
