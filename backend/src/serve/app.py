"""FastAPI REST application for FinNews."""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.src.alloc.engine import AllocationEngine
from backend.src.persona.engine import PersonaEngine
from backend.src.schema import (
    NewsHorizon,
)
from backend.src.stats.engine import StatEngine
from backend.src.store.db import Database


def _latest_scores(db: Database) -> tuple[dict[str, tuple[float, float]], dict[str, str]]:
    """Ambil skor sentimen terakhir per aset dari DB.

    Mengembalikan (scores, sources):
    - scores  : asset_id -> (score, confidence)
    - sources : asset_id -> keterangan asal angka ("db:2026-10-20" / "tanpa_data")

    Aset tanpa baris `daily_sentiment` diberi (0.0, 0.0) — netral dan tanpa
    keyakinan. Ini disengaja: lebih jujur daripada mengarang 0.25/0.70.
    """
    scores: dict[str, tuple[float, float]] = {}
    sources: dict[str, str] = {}
    with db.get_connection() as conn:
        rows = conn.execute(
            """
            SELECT d.asset_id, d.date, d.score_mean,
                   (SELECT AVG(i.confidence) FROM impacts i
                    WHERE i.asset_id = d.asset_id) AS avg_conf
            FROM daily_sentiment d
            JOIN (
                SELECT asset_id, MAX(date) AS mx FROM daily_sentiment GROUP BY asset_id
            ) t ON t.asset_id = d.asset_id AND t.mx = d.date;
            """
        ).fetchall()

    for r in rows:
        asset = r["asset_id"]
        conf = r["avg_conf"] if r["avg_conf"] is not None else 0.5
        scores[asset] = (float(r["score_mean"]), float(conf))
        sources[asset] = f"db:{r['date']}"

    for asset in ("XAU", "SPX", "RATE_UST"):
        if asset not in scores:
            scores[asset] = (0.0, 0.0)
            sources[asset] = "tanpa_data"
    return scores, sources


def create_app(db_path: Path | str = Path("data/finews.db")) -> FastAPI:
    """Creates and configures the FastAPI application."""
    app = FastAPI(
        title="FinNews API",
        version="0.5.0",
        description="REST API for Financial News Sentiment and Market Association System",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    db = Database(db_path=db_path)
    db.init_schema()

    alloc_engine = AllocationEngine()
    persona_engine = PersonaEngine()

    @app.get("/health")
    def health_check() -> dict:
        return {"status": "ok", "version": "0.5.0", "universe_count": 3}

    @app.get("/api/meta")
    def get_meta() -> dict:
        """Returns provenance metadata: mode, versions, freshness, coverage.

        Feeds the GUI Data Provenance Bar and the splash boot screen, so
        ilustrasi is never mistaken for real data (Upgrade.md UI-01).
        """
        facts = db.get_meta_summary()
        has_data = bool(facts["targets"]) and (facts["last_price_date"] or facts["last_news_date"])
        return {
            "status": "ok",
            "mode": "live" if has_data else "empty",
            "api_version": "0.5.0",
            "schema_version": facts["schema_version"],
            "universe_version": facts["universe_version"],
            "model_version": facts["model_version"],
            "params_version": facts["params_version"],
            "calibrated": False,
            "universe_count": facts["universe_count"],
            "targets": facts["targets"],
            "coverage": {
                "articles": facts["articles"],
                "sources": facts["sources"],
                "days_with_news": facts["days_with_news"],
                "last_price_date": facts["last_price_date"],
                "last_news_date": facts["last_news_date"],
                "last_impact_at": facts["last_impact_at"],
            },
            "updated_at": facts["updated_at"],
        }

    @app.get("/api/universe")
    def get_universe() -> list[dict]:
        """Returns the 3 core locked macro targets metadata."""
        return db.get_active_universe()

    @app.get("/api/series/{target}")
    def get_series(
        target: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> dict:
        """Returns paired DailySentiment and PriceRecord time series."""
        if not db.is_valid_target(target):
            raise HTTPException(status_code=404, detail=f"Target {target} not in 3 core locked universe.")

        p_start = start_date or (date.today() - timedelta(days=90))
        p_end = end_date or date.today()

        daily_sentiments = db.query_daily_sentiment(target, p_start, p_end)
        prices = db.query_prices(target, p_start, p_end)

        return {
            "asset_id": target,
            "start_date": p_start.isoformat(),
            "end_date": p_end.isoformat(),
            "sentiments": [s.model_dump() for s in daily_sentiments],
            "prices": [p.model_dump() for p in prices],
        }

    @app.get("/api/impacts/{target}")
    def get_impacts(
        target: str,
        limit: int = Query(default=50, le=200),
    ) -> list[dict]:
        """Returns recent article impacts for a target, with time audit fields.

        Additive keys (published_at, effective_trading_date, session_close,
        timezone) come from a join, so a reader can trace each impact to its
        market session bucket (Upgrade.md UI-02).
        """
        if not db.is_valid_target(target):
            raise HTTPException(status_code=404, detail=f"Target {target} not in 3 core locked universe.")
        impacts = db.query_impacts(target, limit=limit)
        audit = db.query_impact_time_audit(target, limit=limit)
        audit_by_id = {a["article_id"]: a for a in audit}
        out: list[dict] = []
        for imp in impacts:
            d = imp.model_dump()
            a = audit_by_id.get(imp.article_id)
            for key in ("published_at", "language", "effective_trading_date", "session_close", "timezone",
                        "title", "source", "url", "headline_only"):
                d[key] = a[key] if a else None
            d["probs"] = a["probs"] if a else []
            out.append(d)
        return out

    @app.get("/api/stats/{target}")
    def get_stats(
        target: str,
        max_lag: Optional[int] = Query(default=None, ge=0, le=10),
    ) -> list[dict]:
        """Returns statistical econometric results for target.

        Default returns the stored run results. With max_lag set, Spearman is
        recomputed live across lags 0..max_lag on the daily close and
        sentiment series (association workbench, Upgrade.md UI-05). Response
        shape stays StatResult; direction and size of the association can
        change per lag, which the stored rows alone cannot show.
        """
        if not db.is_valid_target(target):
            raise HTTPException(status_code=404, detail=f"Target {target} not in 3 core locked universe.")
        if max_lag is None:
            return [st.model_dump() for st in db.query_stats(target)]
        # Table dates are ISO strings; a wide sentinel range reads the full history.
        broad_start, broad_end = date(2000, 1, 1), date(2100, 1, 1)
        daily = db.query_daily_sentiment(target, broad_start, broad_end)
        prices = db.query_prices(target, broad_start, broad_end)
        frame = StatEngine.frame_from_daily_prices(daily, prices)
        results = StatEngine.compute_spearman_lags(frame, target, max_lag=max_lag)
        return [r.model_dump() for r in results]

    @app.get("/api/allocation")
    def get_allocation_tilt(
        profile_id: str = "moderate",
        article_id: str = "current_market",
    ) -> dict:
        """Returns Allocation Tilt result, dengan skor dari DB (bukan angka tetap).

        S-1: sebelumnya endpoint ini menyajikan angka karangan
        ({"XAU": (0.25, 0.70), ...}) sehingga terlihat seperti hasil analisis
        padahal konstanta. Sekarang skor diambil dari `daily_sentiment`
        terakhir per aset; aset tanpa data diberi skor netral 0.0 dengan
        keyakinan rendah, dan itu dinyatakan terbuka lewat `data_sources`.
        """
        scores, sources = _latest_scores(db)
        class_scores = alloc_engine.compute_class_scores(scores)
        suggestion = alloc_engine.tilt_portfolio(
            article_id=article_id,
            profile_id=profile_id,
            class_scores=class_scores,
        )
        # S-2: simpan agar hasil bisa diaudit ulang, bukan hanya dikembalikan.
        db.save_alloc_suggestion(suggestion)

        payload = suggestion.model_dump()
        payload["data_sources"] = sources
        return payload

    @app.get("/api/persona/{article_id}")
    def get_persona_views(
        article_id: str,
        target: str = "SPX",
        score: Optional[float] = None,
        confidence: Optional[float] = None,
        horizon: Optional[NewsHorizon] = None,
    ) -> list[dict]:
        """Stance 5 persona untuk satu dampak artikel.

        S-1: `score` dan `confidence` dulu punya nilai bawaan karangan
        (0.35 / 0.75) sehingga setiap panggilan tanpa parameter menghasilkan
        "analisis" yang sama persis. Kini bila tidak diberikan, nilainya
        diambil dari `impacts` artikel tersebut; bila artikel tidak punya
        dampak, jawabannya 404 -- bukan angka palsu.

        S-5: `horizon` dulu selalu jatuh ke SHORT karena router tidak pernah
        mengisinya, sehingga semua persona melihat berita berhorizon pendek.
        Kini bila tidak diberikan, diambil dari `impacts.news_horizon`.
        """
        if score is None or confidence is None:
            row = db.get_impact_for_article(article_id, target)
            if row is None:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Tidak ada dampak tercatat untuk artikel '{article_id}' "
                        f"pada target '{target}'. Berikan ?score=&confidence= "
                        "atau jalankan pipeline lebih dulu."
                    ),
                )
            score = row["score"] if score is None else score
            confidence = row["confidence"] if confidence is None else confidence
            if horizon is None and row.get("news_horizon"):
                horizon = NewsHorizon(row["news_horizon"])

        if horizon is None:
            horizon = NewsHorizon.SHORT

        views = persona_engine.evaluate_all(
            article_id=article_id,
            target=target,
            score=score,
            confidence=confidence,
            news_horizon=horizon,
        )
        # S-2: persist supaya reproducible & bisa diperiksa ulang.
        db.save_persona_views(views)
        return [v.model_dump() for v in views]

    return app
