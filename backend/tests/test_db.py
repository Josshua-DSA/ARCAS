"""Tests for SQLite database initialization, seeding, and operations."""

from datetime import date
from pathlib import Path

from backend.src.schema import DailySentiment, PriceRecord


def test_db_seeding(temp_db):
    """Verifies that asset_master and aliases are properly seeded."""
    inserted = temp_db.seed_asset_master(Path("data/universe/asset_master.csv"))
    assert inserted == 3


def test_meta_summary_counts_and_versions(temp_db):
    """get_meta_summary returns real counts and version stamps for /api/meta."""
    temp_db.seed_asset_master(Path("data/universe/asset_master.csv"))
    meta = temp_db.get_meta_summary()
    assert meta["universe_count"] == 3
    assert meta["targets"] == ["RATE_UST", "SPX", "XAU"]
    assert meta["universe_version"] == "2026-10-12-core3"
    # Empty DB: counts are real zeros, never fabricated numbers.
    assert meta["articles"] == 0
    assert meta["last_price_date"] is None
    assert meta["updated_at"] is None


def test_impact_time_audit_on_empty_db(temp_db):
    """Time audit join degrades to real empties, never fake timestamps."""
    temp_db.seed_asset_master(Path("data/universe/asset_master.csv"))
    audit = temp_db.query_impact_time_audit("XAU", limit=10)
    assert audit == []

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


# ==========================================================
# S-7: satu nama untuk satu fungsi
# ==========================================================


def test_init_schema_is_idempotent(temp_db):
    """`init_schema()` aman dipanggil berulang — sifat yang tadinya
    tersembunyi di balik alias `init_tables()`.

    Dua nama untuk satu fungsi membuat pembaca baru mengira keduanya berbeda
    dan menyembunyikan fakta bahwa pemanggilan ulang tidak merusak apa pun.
    """
    temp_db.init_schema()
    temp_db.init_schema()

    # Data yang sudah ada tidak boleh hilang karena skema dibuat ulang.
    temp_db.save_daily_sentiment(
        DailySentiment(
            asset_id="XAU",
            date=date(2026, 10, 1),
            score_mean=0.4,
            score_weighted=0.4,
            n_articles=3,
            n_sources=2,
            has_news=True,
        )
    )
    temp_db.init_schema()
    rows = temp_db.query_daily_sentiment("XAU", date(2026, 10, 1), date(2026, 10, 1))
    assert len(rows) == 1, "init_schema() menghapus data yang sudah ada"


def test_init_tables_alias_is_gone():
    """Alias yang membingungkan tidak boleh kembali."""
    from backend.src.store.db import Database

    assert not hasattr(Database, "init_tables"), (
        "init_tables() adalah alias init_schema(); pakai init_schema() saja"
    )


# -- P1-7: retensi jejak simulasi ------------------------------------------


def test_sim_runs_purge_menghormati_batas_hari(temp_db):
    """Jejak lebih tua dari retensi dihapus; yang baru dipertahankan."""
    import sqlite3
    from datetime import datetime, timedelta

    class Hasil:
        text = "Gold naik tajam"
        input_kind = "berita"
        is_rumor = False
        source = None
        target = "XAU"
        tone = "positive"
        score = 0.5
        confidence = 0.5
        confidence_raw = 0.5
        penalty = 0.0
        direction = "bullish"
        horizon = "pendek"
        model_version = "uji"
        warnings: list = []
        degraded: list = []

    baru = temp_db.save_sim_run(Hasil())
    lama = temp_db.save_sim_run(Hasil())
    assert baru > 0 and lama > 0

    # Mundurkan satu baris melewati batas retensi.
    basi = (datetime.now() - timedelta(days=temp_db.RETAIN_DAYS + 1)).isoformat()
    with sqlite3.connect(temp_db.db_path) as c:
        c.execute("UPDATE sim_runs SET created_at = ? WHERE run_id = ?;", (basi, lama))

    assert temp_db.purge_sim_runs() == 1
    assert temp_db.get_sim_run(lama) is None
    assert temp_db.get_sim_run(baru) is not None


def test_sim_runs_purge_idempoten(temp_db):
    assert temp_db.purge_sim_runs() == 0
    assert temp_db.purge_sim_runs() == 0


def test_get_sim_run_tidak_ada_mengembalikan_none(temp_db):
    assert temp_db.get_sim_run(123456) is None
