"""Tests for SQLite database initialization, seeding, and operations."""

from datetime import date, datetime
from pathlib import Path
import tempfile
import pytest

from backend.src.schema import DailySentiment, PriceRecord, StatResult
from backend.src.store.db import Database


@pytest.fixture
def temp_db():
    # TemporaryDirectory instead of NamedTemporaryFile: sqlite cannot open
    # a still-locked temp handle on Windows ("unable to open database file").
    with tempfile.TemporaryDirectory() as d:
        db = Database(db_path=str(Path(d) / "test.db"))
        db.init_tables()
        yield db


def test_db_seeding(temp_db):
    """Verifies that asset_master and aliases are properly seeded."""
    inserted = temp_db.seed_asset_master(Path("data/universe/asset_master.csv"))
    assert inserted == 3

    universe = temp_db.get_active_universe()
    assert len(universe) == 3
    assert any(u["asset_id"] == "SPX" for u in universe)
    assert any(u["asset_id"] == "XAU" for u in universe)
    assert any(u["asset_id"] == "RATE_UST" for u in universe)

    inserted_aliases = temp_db.seed_aliases(Path("data/universe/aliases.csv"))
    assert inserted_aliases > 0


def test_db_daily_sentiment_crud(temp_db):
    """Tests saving and querying daily sentiments."""
    temp_db.seed_asset_master(Path("data/universe/asset_master.csv"))

    record = DailySentiment(
        asset_id="SPX",
        date=date(2026, 10, 9),
        score_mean=0.25,
        score_weighted=0.30,
        n_articles=5,
        n_sources=3,
        has_news=True,
    )
    temp_db.save_daily_sentiment(record)

    results = temp_db.query_daily_sentiment("SPX", date(2026, 10, 1), date(2026, 10, 10))
    assert len(results) == 1
    assert results[0].score_mean == 0.25
    assert results[0].has_news is True


def test_db_price_crud(temp_db):
    """Tests price storage and retrieval."""
    temp_db.seed_asset_master(Path("data/universe/asset_master.csv"))

    price = PriceRecord(
        asset_id="XAU",
        date=date(2026, 10, 9),
        open=2650.0,
        high=2660.0,
        low=2645.0,
        close=2655.0,
        adj_close=2655.0,
        volume=120000.0,
    )
    temp_db.save_price(price)

    results = temp_db.query_prices("XAU", date(2026, 10, 1), date(2026, 10, 10))
    assert len(results) == 1
    assert results[0].close == 2655.0
