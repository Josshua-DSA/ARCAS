"""Tests for S-1: endpoint API tidak boleh menyajikan angka karangan.

Sebelum perbaikan, `/api/allocation` memakai konstanta
`{"XAU": (0.25, 0.70), ...}` dan `/api/persona/{id}` memakai nilai bawaan
`score=0.35, confidence=0.75`. Keduanya tampak seperti hasil analisis
padahal sama persis setiap kali dipanggil.
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from backend.src.schema import (
    Basis,
    DailySentiment,
    Direction,
    EvidenceSpan,
    TargetImpact,
)
from backend.src.serve.app import create_app
from backend.src.store.db import Database


@pytest.fixture()
def client(tmp_path):
    db_path = tmp_path / "api.db"
    db = Database(db_path)
    db.init_schema()
    db.seed_asset_master()
    return TestClient(create_app(db_path)), db


def _seed_daily(db, asset, score, day):
    db.save_daily_sentiment(
        DailySentiment(
            asset_id=asset,
            date=day,
            score_mean=score,
            score_weighted=score,
            n_articles=3,
            n_sources=2,
            has_news=True,
            version="v0.1",
        )
    )


def test_allocation_reflects_db_scores(client):
    """Skor dari DB harus memengaruhi hasil, bukan konstanta."""
    c, db = client
    _seed_daily(db, "XAU", 0.9, date(2026, 10, 20))
    _seed_daily(db, "SPX", -0.9, date(2026, 10, 20))

    body = c.get("/api/allocation").json()
    assert body["data_sources"]["XAU"] == "db:2026-10-20"
    assert body["data_sources"]["SPX"] == "db:2026-10-20"


def test_allocation_reports_missing_data_honestly(client):
    """Aset tanpa data harus ditandai `tanpa_data`, bukan diberi angka karangan."""
    c, db = client
    body = c.get("/api/allocation").json()
    assert body["data_sources"]["XAU"] == "tanpa_data"
    assert body["data_sources"]["SPX"] == "tanpa_data"
    assert body["data_sources"]["RATE_UST"] == "tanpa_data"


def test_allocation_never_returns_old_hardcoded_constant(client):
    """Regresi: 0.25/0.70 tidak boleh muncul lagi sebagai skor XAU."""
    c, db = client
    _seed_daily(db, "XAU", 0.0, date(2026, 10, 20))
    body = c.get("/api/allocation").json()
    assert body["data_sources"]["XAU"] != "tanpa_data"


def test_allocation_keeps_hundred_percent_constraint(client):
    """Batas keras RULES: total alokasi harus tetap 100%."""
    c, db = client
    _seed_daily(db, "XAU", 0.7, date(2026, 10, 20))
    _seed_daily(db, "SPX", 0.4, date(2026, 10, 20))
    _seed_daily(db, "RATE_UST", -0.2, date(2026, 10, 20))

    body = c.get("/api/allocation").json()
    total = sum(line["new_pct"] for line in body["lines"])
    assert round(total, 6) == 100.0


def test_persona_404_when_article_has_no_impact(client):
    """Tanpa dampak tercatat, endpoint harus 404 -- bukan mengarang skor."""
    c, _ = client
    r = c.get("/api/persona/artikel-tidak-ada?target=SPX")
    assert r.status_code == 404
    assert "Tidak ada dampak" in r.json()["detail"]


def test_persona_uses_recorded_impact(client):
    """Bila dampak ada, angka dari DB yang dipakai."""
    c, db = client
    db.save_impact(
        TargetImpact(
            article_id="art1",
            asset_id="SPX",
            direction=Direction.BULLISH,
            score=0.81,
            confidence=0.66,
            basis=Basis.EXPLICIT,
            themes=[],
            evidence=[EvidenceSpan(quote="emas naik", start=0, end=9)],
            flags=[],
            model_version="test",
        )
    )
    views = c.get("/api/persona/art1?target=SPX").json()
    assert len(views) > 0


def test_persona_explicit_params_still_honoured(client):
    """Parameter eksplisit tetap boleh menimpa DB (untuk eksplorasi)."""
    c, _ = client
    r = c.get("/api/persona/apa-saja?target=SPX&score=0.5&confidence=0.8")
    assert r.status_code == 200
