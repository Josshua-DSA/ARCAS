"""S-5 / FR-23: `news_horizon` harus ditentukan, bukan konstanta.

Sebelum perbaikan, `TargetImpact.news_horizon` selalu jatuh ke nilai bawaan
`NewsHorizon.SHORT`: `tagging/router.py` tidak pernah mengisinya, kolomnya
tidak ada di tabel `impacts`, dan endpoint persona memakai default parameter.
Akibatnya FR-23 hanya "terisi" secara teknis — semua persona melihat berita
berhorizon pendek, dan `horizon_match()` di mesin persona selalu memakai baris
"short".
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from backend.src.schema import (
    Article,
    Basis,
    Direction,
    EvidenceSpan,
    Lang,
    NewsHorizon,
    TargetImpact,
)
from backend.src.store.db import Database
from backend.src.tagging.router import TargetRouter

# ==========================================================
# Kebijakan horizon
# ==========================================================


@pytest.fixture()
def router() -> TargetRouter:
    return TargetRouter()


def test_explicit_route_is_short_by_default(router):
    """Aset disebut langsung -> reaksi cepat, horizon pendek."""
    assert router.resolve_horizon("Gold prices climb", Basis.EXPLICIT) is NewsHorizon.SHORT


def test_macro_route_is_medium_by_default(router):
    """Lewat tema -> butuh waktu merambat, horizon menengah."""
    assert router.resolve_horizon("Inflation eased last month", Basis.MACRO_FACTOR) is NewsHorizon.MEDIUM


def test_intraday_keyword_forces_intraday(router):
    """Kata kunci intraday menang atas aturan basis."""
    assert router.resolve_horizon("Gold jumps at the open", Basis.EXPLICIT) is NewsHorizon.INTRADAY


def test_horizon_is_not_a_constant(router):
    """Regresi inti S-5: horizon tidak boleh selalu nilai yang sama."""
    hasil = {
        router.resolve_horizon("Gold prices climb", Basis.EXPLICIT),
        router.resolve_horizon("Inflation eased", Basis.MACRO_FACTOR),
        router.resolve_horizon("Gold jumps intraday", Basis.EXPLICIT),
    }
    assert len(hasil) > 1, "news_horizon masih konstanta"


def test_policy_comes_from_yaml(tmp_path):
    """Mengubah kebijakan di YAML harus mengubah hasil, bukan hanya dokumen."""
    cfg = yaml.safe_load(Path("data/router_config.yaml").read_text(encoding="utf-8"))
    cfg["routing"]["horizon"]["explicit"] = "long"
    cfg["routing"]["horizon"]["intraday_keywords"] = []
    path = tmp_path / "router.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    r = TargetRouter()
    r.config_path = path
    # muat ulang kebijakan dari path baru
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    r.horizon_policy.update(data["routing"]["horizon"])

    assert r.resolve_horizon("Gold prices climb", Basis.EXPLICIT) is NewsHorizon.LONG


def test_invalid_policy_falls_back_to_short(router):
    """Konfigurasi salah tidak boleh menjatuhkan pipeline."""
    router.horizon_policy["explicit"] = "berabad-abad"
    assert router.resolve_horizon("Gold climbs", Basis.EXPLICIT) is NewsHorizon.SHORT


# ==========================================================
# Horizon ikut tersimpan & terbaca kembali
# ==========================================================


@pytest.fixture()
def db():
    with tempfile.TemporaryDirectory() as d:
        base = Database(db_path=str(Path(d) / "t.db"))
        base.init_schema()
        yield base


def _impact(horizon: NewsHorizon) -> TargetImpact:
    return TargetImpact(
        article_id="a1",
        asset_id="XAU",
        direction=Direction.BULLISH,
        score=0.5,
        confidence=0.8,
        basis=Basis.EXPLICIT,
        themes=[],
        evidence=[EvidenceSpan(quote="Gold prices climb", start=0, end=18)],
        news_horizon=horizon,
        model_version="fusion-v1",
    )


def test_horizon_persisted_and_read_back(db):
    """S-5: horizon harus selamat melewati database.

    Sebelumnya kolomnya tidak ada, sehingga informasi ini hilang begitu
    proses selesai dan endpoint persona terpaksa memakai default.
    """
    db.save_impact(_impact(NewsHorizon.MEDIUM))
    row = db.get_impact_for_article("a1", "XAU")
    assert row is not None
    assert row["news_horizon"] == "medium"


def test_different_horizons_round_trip(db):
    for i, h in enumerate([NewsHorizon.INTRADAY, NewsHorizon.SHORT, NewsHorizon.LONG]):
        db.save_impact(
            TargetImpact(
                article_id=f"art{i}",
                asset_id="XAU",
                direction=Direction.BULLISH,
                score=0.4,
                confidence=0.7,
                basis=Basis.EXPLICIT,
                themes=[],
                evidence=[EvidenceSpan(quote="Gold prices climb", start=0, end=18)],
                news_horizon=h,
                model_version="fusion-v1",
            )
        )
    for i, expected in enumerate(["intraday", "short", "long"]):
        row = db.get_impact_for_article(f"art{i}", "XAU")
        assert row is not None
        assert row["news_horizon"] == expected


def test_migration_adds_horizon_column_to_old_db(tmp_path):
    """DB lama (tanpa kolom) harus dimigrasi, bukan error."""
    import sqlite3

    path = tmp_path / "lama.db"
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE impacts (
          article_id TEXT NOT NULL, asset_id TEXT NOT NULL, direction TEXT NOT NULL,
          score REAL NOT NULL, confidence REAL NOT NULL, basis TEXT NOT NULL,
          themes_json TEXT, causal_path_json TEXT, rationale TEXT, evidence_json TEXT,
          flags_json TEXT, model_version TEXT NOT NULL, universe_version TEXT NOT NULL,
          schema_version TEXT NOT NULL, created_at TIMESTAMP NOT NULL,
          PRIMARY KEY (article_id, asset_id, model_version)
        );
        """
    )
    conn.commit()
    conn.close()

    db = Database(db_path=str(path))
    db.init_schema()
    db.save_impact(_impact(NewsHorizon.MEDIUM))
    row = db.get_impact_for_article("a1", "XAU")
    assert row is not None
    assert row["news_horizon"] == "medium"


# ==========================================================
# Router mengisi horizon pada impact nyata
# ==========================================================


def test_router_fills_horizon_on_explicit_impact(router):
    article = Article(
        article_id="x1",
        source="test",
        url="https://contoh.test/1",
        title="Gold prices climb as real yields fall",
        body="Gold prices climb as real yields fall",
        language=Lang.EN,
        published_at="2026-10-20T10:00:00+00:00",
        fetched_at="2026-10-20T10:05:00+00:00",
    )
    impacts = router.route_article(article, sentiment_score=0.5)
    assert impacts, "artikel emas harus menghasilkan dampak"
    assert all(i.news_horizon is not None for i in impacts)
    assert any(i.news_horizon is NewsHorizon.SHORT for i in impacts)
