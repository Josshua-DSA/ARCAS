"""Integration test: routing decision tercatat di DB dan bisa dibaca kembali."""

from datetime import datetime
from pathlib import Path

import pytest

from backend.src.schema import Article, Basis, Direction, Lang, TargetImpact
from backend.src.store.db import Database
from backend.src.tagging.model_router import ModelRouter
from backend.src.tagging.router import TargetRouter


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    d = Database(tmp_path / "t.db")
    d.init_schema()
    return d


def test_migration_adds_route_columns(tmp_path: Path) -> None:
    d = Database(tmp_path / "m.db")
    d.init_schema()
    d.init_schema()  # idempoten
    with d.get_connection() as conn:
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(impacts);").fetchall()}
    assert {"routed_from", "route_score"} <= cols


def test_route_then_persist_keeps_audit_trail(db: Database) -> None:
    router = ModelRouter()
    tagger = TargetRouter()
    article = Article(
        article_id="a1",
        source="reuters",
        title="Gold hits record as Fed pauses",
        body="Bullion extended gains after the Fed signalled a pause.",
        language=Lang.EN,
        published_at=datetime(2026, 10, 19, 12, 0),
        fetched_at=datetime(2026, 10, 19, 12, 5),
    )

    impacts = tagger.route_article(article, sentiment_score=0.4, model_router=router)
    assert impacts, "harus ada minimal satu impact"
    for imp in impacts:
        assert imp.routed_from is not None
        assert imp.routed_from.startswith(("keyword:", "source:", "log_odds:"))
        db.save_impact(imp)

    back = db.query_impacts("XAU")
    assert back and back[0].routed_from == impacts[0].routed_from
    assert back[0].route_score == impacts[0].route_score


def test_impact_without_router_stays_null(db: Database) -> None:
    """Backward-compatible: tanpa router, kolom audit tetap kosong."""
    impact = TargetImpact(
        article_id="a2",
        asset_id="XAU",
        direction=Direction.BULLISH,
        score=0.3,
        confidence=0.5,
        basis=Basis.MACRO_FACTOR,
        themes=["safe_haven"],
        model_version="fusion-v1",
    )
    db.save_impact(impact)
    back = db.query_impacts("XAU")
    assert back[0].routed_from is None and back[0].route_score is None
