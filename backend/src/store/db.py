"""SQLite database repository adhering to SCHEMA v0.5.0."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Generator, Optional

from backend.src.schema import DailySentiment, PriceRecord, StatResult, TargetImpact


DEFAULT_DB_PATH = Path("data/finews.db")


DDL_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_articles (
  raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL,
  url TEXT,
  title TEXT NOT NULL,
  body TEXT,
  published_at TIMESTAMP,
  fetched_at TIMESTAMP NOT NULL,
  query_target TEXT,
  vendor_sentiment REAL,
  payload_json TEXT
);

CREATE TABLE IF NOT EXISTS articles (
  article_id TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  url TEXT,
  title TEXT NOT NULL,
  body TEXT,
  language TEXT NOT NULL,
  published_at TIMESTAMP,
  fetched_at TIMESTAMP NOT NULL,
  duplicate_of TEXT,
  market_relevant BOOLEAN
);

CREATE TABLE IF NOT EXISTS article_targets (
  article_id TEXT NOT NULL REFERENCES articles(article_id),
  asset_id TEXT NOT NULL,
  basis TEXT NOT NULL,
  matched_text TEXT,
  routed_from TEXT,
  effective_trading_date DATE,
  PRIMARY KEY (article_id, asset_id)
);

CREATE TABLE IF NOT EXISTS sentiments (
  article_id TEXT NOT NULL REFERENCES articles(article_id),
  model TEXT NOT NULL,
  model_version TEXT NOT NULL,
  p_pos REAL NOT NULL,
  p_neu REAL NOT NULL,
  p_neg REAL NOT NULL,
  translation_used BOOLEAN DEFAULT 0,
  translator_version TEXT,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, model, model_version)
);

CREATE TABLE IF NOT EXISTS impacts (
  article_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  direction TEXT NOT NULL,
  score REAL NOT NULL,
  confidence REAL NOT NULL,
  basis TEXT NOT NULL,
  themes_json TEXT,
  causal_path_json TEXT,
  rationale TEXT,
  evidence_json TEXT,
  flags_json TEXT,
  model_version TEXT NOT NULL,
  universe_version TEXT NOT NULL,
  schema_version TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, asset_id, model_version)
);

CREATE TABLE IF NOT EXISTS daily_sentiment (
  asset_id TEXT NOT NULL,
  date DATE NOT NULL,
  score_mean REAL,
  score_weighted REAL,
  n_articles INTEGER NOT NULL,
  n_sources INTEGER NOT NULL,
  has_news BOOLEAN NOT NULL,
  version TEXT NOT NULL,
  PRIMARY KEY (asset_id, date, version)
);

CREATE TABLE IF NOT EXISTS prices (
  asset_id TEXT NOT NULL,
  date DATE NOT NULL,
  open REAL,
  high REAL,
  low REAL,
  close REAL,
  adj_close REAL,
  volume REAL,
  PRIMARY KEY (asset_id, date)
);

CREATE TABLE IF NOT EXISTS stat_results (
  run_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  test TEXT NOT NULL,
  market_metric TEXT NOT NULL,
  lag INTEGER,
  estimate REAL NOT NULL,
  ci_low REAL,
  ci_high REAL,
  p_value REAL NOT NULL,
  p_adjusted REAL,
  n_obs INTEGER NOT NULL,
  period_start DATE NOT NULL,
  period_end DATE NOT NULL,
  params_json TEXT NOT NULL,
  code_version TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS labels (
  article_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  annotator TEXT NOT NULL,
  label TEXT NOT NULL,
  labeled_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, asset_id, annotator)
);

CREATE TABLE IF NOT EXISTS asset_master (
  asset_id TEXT PRIMARY KEY,
  asset_class TEXT NOT NULL,
  track TEXT NOT NULL,
  name TEXT NOT NULL,
  price_ticker TEXT NOT NULL,
  exchange TEXT,
  country TEXT,
  sector TEXT,
  timezone TEXT NOT NULL,
  session_close TEXT NOT NULL,
  valid_from DATE NOT NULL,
  valid_to DATE,
  active BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS asset_aliases (
  asset_id TEXT NOT NULL,
  alias TEXT NOT NULL,
  lang TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alloc_profiles (
  profile_id TEXT NOT NULL,
  alloc_class TEXT NOT NULL,
  base_pct REAL NOT NULL,
  min_pct REAL NOT NULL,
  max_pct REAL NOT NULL,
  PRIMARY KEY (profile_id, alloc_class)
);

CREATE TABLE IF NOT EXISTS alloc_suggestions (
  article_id TEXT NOT NULL,
  profile_id TEXT NOT NULL,
  alloc_class TEXT NOT NULL,
  baseline_pct REAL NOT NULL,
  new_pct REAL NOT NULL,
  delta_pp REAL NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT,
  no_change BOOLEAN NOT NULL DEFAULT 0,
  params_version TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, profile_id, alloc_class, params_version)
);

CREATE TABLE IF NOT EXISTS persona_views (
  article_id TEXT NOT NULL,
  persona_id TEXT NOT NULL,
  target TEXT NOT NULL,
  stance TEXT NOT NULL,
  strength REAL NOT NULL,
  news_horizon TEXT NOT NULL,
  raw_value REAL NOT NULL,
  confidence REAL NOT NULL,
  rationale TEXT,
  params_version TEXT NOT NULL,
  created_at TIMESTAMP NOT NULL,
  PRIMARY KEY (article_id, persona_id, target, params_version)
);

CREATE INDEX IF NOT EXISTS idx_impacts_asset ON impacts(asset_id, created_at);
CREATE INDEX IF NOT EXISTS idx_daily_asset_date ON daily_sentiment(asset_id, date);
CREATE INDEX IF NOT EXISTS idx_prices_asset_date ON prices(asset_id, date);
"""


class Database:
    """Manages SQLite connections and queries for FInews."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        """Initializes tables and indexes."""
        with self.get_connection() as conn:
            conn.executescript(DDL_SCHEMA)

    def seed_asset_master(self, csv_path: Path | str = Path("data/universe/asset_master.csv")) -> int:
        """Seeds the 10 locked assets from asset_master.csv."""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            return 0

        inserted = 0
        import csv
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with self.get_connection() as conn:
                for row in reader:
                    conn.execute(
                        """
                        INSERT INTO asset_master (
                            asset_id, asset_class, track, name, price_ticker, exchange,
                            country, sector, timezone, session_close, valid_from, valid_to, active
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(asset_id) DO UPDATE SET
                            name = excluded.name,
                            price_ticker = excluded.price_ticker,
                            session_close = excluded.session_close,
                            active = excluded.active;
                        """,
                        (
                            row["asset_id"],
                            row["asset_class"],
                            row["track"],
                            row["name"],
                            row["price_ticker"],
                            row["exchange"] or None,
                            row["country"] or None,
                            row["sector"] or None,
                            row["timezone"],
                            row["session_close"],
                            row["valid_from"],
                            row["valid_to"] or None,
                            1 if row["active"].lower() in ("true", "1") else 0,
                        ),
                    )
                    inserted += 1
        return inserted

    def seed_aliases(self, csv_path: Path | str = Path("data/universe/aliases.csv")) -> int:
        """Seeds asset aliases from aliases.csv."""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            return 0

        import csv
        inserted = 0
        with open(csv_file, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with self.get_connection() as conn:
                conn.execute("DELETE FROM asset_aliases;")
                for row in reader:
                    conn.execute(
                        "INSERT INTO asset_aliases (asset_id, alias, lang) VALUES (?, ?, ?);",
                        (row["asset_id"], row["alias"].strip().lower(), row["lang"]),
                    )
                    inserted += 1
        return inserted

    def save_impact(self, impact: TargetImpact) -> None:
        """Stores a TargetImpact record."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO impacts (
                    article_id, asset_id, direction, score, confidence, basis,
                    themes_json, causal_path_json, rationale, evidence_json, flags_json,
                    model_version, universe_version, schema_version, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    impact.article_id,
                    impact.asset_id,
                    impact.direction.value,
                    impact.score,
                    impact.confidence,
                    impact.basis.value,
                    json.dumps(impact.themes),
                    json.dumps(impact.causal_path) if impact.causal_path else None,
                    impact.rationale,
                    json.dumps([e.model_dump() for e in impact.evidence]),
                    json.dumps(impact.flags),
                    impact.model_version,
                    impact.universe_version,
                    impact.schema_version,
                    impact.created_at.isoformat(),
                ),
            )

    def save_daily_sentiment(self, daily: DailySentiment) -> None:
        """Stores daily aggregate sentiment for an asset."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO daily_sentiment (
                    asset_id, date, score_mean, score_weighted,
                    n_articles, n_sources, has_news, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    daily.asset_id,
                    daily.date.isoformat(),
                    daily.score_mean,
                    daily.score_weighted,
                    daily.n_articles,
                    daily.n_sources,
                    1 if daily.has_news else 0,
                    daily.version,
                ),
            )

    def save_price(self, price: PriceRecord) -> None:
        """Stores a daily asset price."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO prices (
                    asset_id, date, open, high, low, close, adj_close, volume
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    price.asset_id,
                    price.date.isoformat(),
                    price.open,
                    price.high,
                    price.low,
                    price.close,
                    price.adj_close,
                    price.volume,
                ),
            )

    def init_tables(self) -> None:
        """Alias for init_schema."""
        self.init_schema()

    def get_active_universe(self) -> list[dict]:
        """Returns all 3 active universe assets."""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM asset_master WHERE active = 1 ORDER BY asset_id ASC;"
            ).fetchall()
            return [dict(r) for r in rows]

    def is_valid_target(self, target: str) -> bool:
        """Checks if a target belongs to the 3 locked universe."""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT 1 FROM asset_master WHERE asset_id = ? AND active = 1;", (target,)
            ).fetchone()
            if row:
                return True
            # Fallback if DB not seeded yet
            locked = {"XAU", "RATE_UST", "SPX"}
            return target in locked

    def query_daily_sentiment(
        self, asset_id: str, start_date: date, end_date: date
    ) -> list[DailySentiment]:
        """Queries daily sentiment records between dates."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT asset_id, date, score_mean, score_weighted, n_articles, n_sources, has_news, version
                FROM daily_sentiment
                WHERE asset_id = ? AND date >= ? AND date <= ?
                ORDER BY date ASC;
                """,
                (asset_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

            res: list[DailySentiment] = []
            for r in rows:
                res.append(
                    DailySentiment(
                        asset_id=r["asset_id"],
                        date=date.fromisoformat(r["date"]),
                        score_mean=r["score_mean"],
                        score_weighted=r["score_weighted"],
                        n_articles=r["n_articles"],
                        n_sources=r["n_sources"],
                        has_news=bool(r["has_news"]),
                        version=r["version"],
                    )
                )
            return res

    def query_prices(
        self, asset_id: str, start_date: date, end_date: date
    ) -> list[PriceRecord]:
        """Queries price records between dates."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT asset_id, date, open, high, low, close, adj_close, volume
                FROM prices
                WHERE asset_id = ? AND date >= ? AND date <= ?
                ORDER BY date ASC;
                """,
                (asset_id, start_date.isoformat(), end_date.isoformat()),
            ).fetchall()

            res: list[PriceRecord] = []
            for r in rows:
                res.append(
                    PriceRecord(
                        asset_id=r["asset_id"],
                        date=date.fromisoformat(r["date"]),
                        open=r["open"],
                        high=r["high"],
                        low=r["low"],
                        close=r["close"],
                        adj_close=r["adj_close"],
                        volume=r["volume"],
                    )
                )
            return res

    def query_impacts(self, asset_id: str, limit: int = 50) -> list[TargetImpact]:
        """Queries recent target impacts."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM impacts
                WHERE asset_id = ?
                ORDER BY created_at DESC
                LIMIT ?;
                """,
                (asset_id, limit),
            ).fetchall()

            res: list[TargetImpact] = []
            for r in rows:
                from backend.src.schema import Basis, Direction, EvidenceSpan
                themes = json.loads(r["themes_json"]) if r["themes_json"] else []
                causal = json.loads(r["causal_path_json"]) if r["causal_path_json"] else None
                evidence_raw = json.loads(r["evidence_json"]) if r["evidence_json"] else []
                flags = json.loads(r["flags_json"]) if r["flags_json"] else []

                evidence = [EvidenceSpan(**e) for e in evidence_raw]

                res.append(
                    TargetImpact(
                        article_id=r["article_id"],
                        asset_id=r["asset_id"],
                        direction=Direction(r["direction"]),
                        score=r["score"],
                        confidence=r["confidence"],
                        basis=Basis(r["basis"]),
                        themes=themes,
                        causal_path=causal,
                        rationale=r["rationale"],
                        evidence=evidence,
                        flags=flags,
                        model_version=r["model_version"],
                        universe_version=r["universe_version"],
                        schema_version=r["schema_version"],
                        created_at=datetime.fromisoformat(r["created_at"]),
                    )
                )
            return res

    def save_stat(self, stat: StatResult) -> None:
        """Stores econometric test result."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO stat_results (
                    run_id, asset_id, test, market_metric, lag, estimate,
                    ci_low, ci_high, p_value, p_adjusted, n_obs,
                    period_start, period_end, params_json, code_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    stat.run_id,
                    stat.asset_id,
                    stat.test,
                    stat.market_metric,
                    stat.lag,
                    stat.estimate,
                    stat.ci_low,
                    stat.ci_high,
                    stat.p_value,
                    stat.p_adjusted,
                    stat.n_obs,
                    stat.period_start.isoformat(),
                    stat.period_end.isoformat(),
                    stat.params_json,
                    stat.code_version,
                ),
            )

    def query_stats(self, asset_id: str) -> list[StatResult]:
        """Queries recent econometric results for asset."""
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM stat_results
                WHERE asset_id = ?
                ORDER BY rowid DESC
                LIMIT 50;
                """,
                (asset_id,),
            ).fetchall()

            res: list[StatResult] = []
            for r in rows:
                res.append(
                    StatResult(
                        run_id=r["run_id"],
                        asset_id=r["asset_id"],
                        test=r["test"],
                        market_metric=r["market_metric"],
                        lag=r["lag"],
                        estimate=r["estimate"],
                        ci_low=r["ci_low"],
                        ci_high=r["ci_high"],
                        p_value=r["p_value"],
                        p_adjusted=r["p_adjusted"],
                        n_obs=r["n_obs"],
                        period_start=date.fromisoformat(r["period_start"]),
                        period_end=date.fromisoformat(r["period_end"]),
                        params_json=r["params_json"],
                        code_version=r["code_version"],
                    )
                )
            return res

    def get_daily_series(self, asset_id: str, start_date: Optional[date] = None) -> list[dict]:
        """Retrieves joint sentiment and price series for a target."""
        query = """
            SELECT
                p.date,
                p.close,
                p.volume,
                d.score_mean,
                d.n_articles,
                d.has_news
            FROM prices p
            LEFT JOIN daily_sentiment d ON p.asset_id = d.asset_id AND p.date = d.date
            WHERE p.asset_id = ?
        """
        params: list[str] = [asset_id]
        if start_date:
            query += " AND p.date >= ?"
            params.append(start_date.isoformat())
        query += " ORDER BY p.date ASC;"

        with self.get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
