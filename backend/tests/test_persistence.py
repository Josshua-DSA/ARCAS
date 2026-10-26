"""Tests for S-2: persona_views & alloc_suggestions harus dipersistensi.

NFR reproducibility menuntut hasil analisis bisa diperiksa ulang. Sebelum
perbaikan, kedua tabel ada di skema tetapi tidak pernah ditulisi: hasil
dihitung, dikirim ke klien, lalu hilang.
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
def env(tmp_path):
    db_path = tmp_path / "persist.db"
    db = Database(db_path)
    db.init_schema()
    db.seed_asset_master()
    db.save_daily_sentiment(
        DailySentiment(
            asset_id="XAU",
            date=date(2026, 10, 20),
            score_mean=0.6,
            score_weighted=0.6,
            n_articles=3,
            n_sources=2,
            has_news=True,
            version="v1",
        )
    )
    db.save_impact(
        TargetImpact(
            article_id="art1",
            asset_id="SPX",
            direction=Direction.BULLISH,
            score=0.8,
            confidence=0.7,
            basis=Basis.EXPLICIT,
            themes=[],
            evidence=[EvidenceSpan(quote="saham naik", start=0, end=10)],
            flags=[],
            model_version="test",
        )
    )
    return TestClient(create_app(db_path)), db


def test_allocation_response_is_persisted(env):
    c, db = env
    c.get("/api/allocation")
    rows = db.get_alloc_suggestions("current_market")
    assert len(rows) > 0, "alloc_suggestions harus terisi setelah endpoint dipanggil"
    assert sum(r["new_pct"] for r in rows) == pytest.approx(100.0, abs=1e-6)


def test_persona_response_is_persisted(env):
    c, db = env
    c.get("/api/persona/art1?target=SPX")
    rows = db.get_persona_views("art1")
    assert len(rows) == 5, "kelima persona harus tersimpan"


def test_persisted_persona_matches_response(env):
    """Yang disimpan harus sama dengan yang dikirim ke klien."""
    c, db = env
    views = c.get("/api/persona/art1?target=SPX").json()
    stored = {r["persona_id"]: r for r in db.get_persona_views("art1")}

    assert set(stored) == {v["persona_id"] for v in views}
    for v in views:
        row = stored[v["persona_id"]]
        assert row["stance"] == v["stance"]
        assert row["strength"] == pytest.approx(v["strength"], abs=1e-9)


def test_repeat_calls_do_not_duplicate(env):
    """Pemanggilan ulang harus menimpa, bukan menumpuk baris kembar."""
    c, db = env
    c.get("/api/persona/art1?target=SPX")
    c.get("/api/persona/art1?target=SPX")
    assert len(db.get_persona_views("art1")) == 5


def test_persona_not_stored_when_endpoint_404(env):
    """Tidak ada dampak -> tidak ada yang disimpan (jangan simpan karangan)."""
    c, db = env
    r = c.get("/api/persona/artikel-misterius?target=XAU")
    assert r.status_code == 404
    assert db.get_persona_views("artikel-misterius") == []


def test_alloc_rows_cover_all_classes(env):
    c, db = env
    c.get("/api/allocation")
    classes = {r["alloc_class"] for r in db.get_alloc_suggestions("current_market")}
    assert len(classes) == 5
    assert "gold" in classes and "stock" in classes


def test_persisted_rows_carry_provenance(env):
    """Audit butuh jejak: versi parameter dan waktu pembuatan."""
    c, db = env
    c.get("/api/persona/art1?target=SPX")
    row = db.get_persona_views("art1")[0]
    assert row["params_version"]
    assert row["created_at"]
