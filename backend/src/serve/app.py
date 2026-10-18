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
from backend.src.store.db import Database


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
    db.init_tables()

    alloc_engine = AllocationEngine()
    persona_engine = PersonaEngine()

    @app.get("/health")
    def health_check() -> dict:
        return {"status": "ok", "version": "0.5.0", "universe_count": 3}

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
        """Returns recent article impacts for a target."""
        if not db.is_valid_target(target):
            raise HTTPException(status_code=404, detail=f"Target {target} not in 3 core locked universe.")
        impacts = db.query_impacts(target, limit=limit)
        return [imp.model_dump() for imp in impacts]

    @app.get("/api/stats/{target}")
    def get_stats(target: str) -> list[dict]:
        """Returns statistical econometric results for target."""
        if not db.is_valid_target(target):
            raise HTTPException(status_code=404, detail=f"Target {target} not in 3 core locked universe.")
        stats = db.query_stats(target)
        return [st.model_dump() for st in stats]

    @app.get("/api/allocation")
    def get_allocation_tilt(
        profile_id: str = "moderate",
        article_id: str = "current_market",
    ) -> dict:
        """Returns Allocation Tilt simulation result adhering to 100% constraint."""
        # Derive current class scores across active universe
        # In full run: pulls latest daily sentiment score for key assets
        scores = {
            "XAU": (0.25, 0.70),
            "SPX": (0.20, 0.80),
            "RATE_UST": (0.10, 0.65),
        }
        class_scores = alloc_engine.compute_class_scores(scores)
        suggestion = alloc_engine.tilt_portfolio(
            article_id=article_id,
            profile_id=profile_id,
            class_scores=class_scores,
        )
        return suggestion.model_dump()

    @app.get("/api/persona/{article_id}")
    def get_persona_views(
        article_id: str,
        target: str = "SPX",
        score: float = 0.35,
        confidence: float = 0.75,
        horizon: NewsHorizon = NewsHorizon.SHORT,
    ) -> list[dict]:
        """Evaluates stances of 5 investor personas for an article impact."""
        views = persona_engine.evaluate_all(
            article_id=article_id,
            target=target,
            score=score,
            confidence=confidence,
            news_horizon=horizon,
        )
        return [v.model_dump() for v in views]

    return app
