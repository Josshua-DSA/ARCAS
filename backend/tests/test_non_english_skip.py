"""Test kebijakan: artikel non-Inggris tidak ikut scoring sentimen.

Terjemahan ID->EN MATI 2026-10-11 (context/DESIGN.md §3.1 #4) dan FinBERT-EMAS
maupun FOMC-RoBERTa hanya dilatih pada teks Inggris. Memaksa teks Indonesia
lewat model Inggris menghasilkan skor yang menyesatkan — terbukti sebelum
perbaikan ini: "Harga emas anjlok tajam setelah bank sentral menaikkan suku
bunga" (negatif) diskor `positive` +0.231, lalu masuk agregasi harian sebagai
sinyal bullish palsu.

Karena itu pipeline melewati artikel non-Inggris untuk scoring, tetapi tetap
menyimpannya di tabel `articles` agar data mentah tidak hilang.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.src.pipeline import Pipeline
from backend.src.pipeline.runner import PipelineStats
from backend.src.schema import Article, Lang
from backend.src.store.db import Database


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    database = Database(tmp_path / "t.db")
    database.init_schema()
    return database


def _artikel(article_id: str, judul: str, bahasa: Lang) -> Article:
    now = datetime(2026, 10, 23, 10, 0, 0, tzinfo=timezone.utc)
    return Article(
        article_id=article_id,
        source="reuters",
        url=f"https://example.com/{article_id}",
        title=judul,
        body="",
        language=bahasa,
        published_at=now,
        fetched_at=now,
        effective_trading_date={},
    )


def test_artikel_indonesia_dilewati_tapi_tersimpan(db: Database) -> None:
    """Artikel ID: masuk `articles`, tidak masuk `sentiments`/`impacts`."""
    pipe = Pipeline(db_path=db.db_path)
    artikel = _artikel(
        "id-1",
        "Harga emas anjlok tajam setelah bank sentral menaikkan suku bunga",
        Lang.ID,
    )
    db.save_articles([artikel])

    impacts, stats = pipe.score_and_route([artikel], dry_run=False)

    assert stats.artikel_bukan_inggris == 1
    assert impacts == []
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM articles").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM sentiments").fetchone()[0] == 0


def test_artikel_inggris_tetap_diskor(db: Database) -> None:
    """Kontrol: artikel EN harus tetap diskor (kebijakan tidak terlalu luas)."""
    pipe = Pipeline(db_path=db.db_path)
    artikel = _artikel(
        "en-1",
        "Gold surges to record high as dollar weakens",
        Lang.EN,
    )
    db.save_articles([artikel])

    impacts, stats = pipe.score_and_route([artikel], dry_run=False)

    assert stats.artikel_bukan_inggris == 0
    assert len(impacts) == 1
    with sqlite3.connect(db.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM sentiments").fetchone()[0] == 1


def test_lang_other_juga_dilewati(db: Database) -> None:
    """`Lang.OTHER` tidak punya model yang sesuai, jadi juga dilewati."""
    pipe = Pipeline(db_path=db.db_path)
    artikel = _artikel("other-1", "Preis Gold steigt stark an", Lang.OTHER)
    db.save_articles([artikel])

    impacts, stats = pipe.score_and_route([artikel], dry_run=False)

    assert stats.artikel_bukan_inggris == 1
    assert impacts == []


def test_statistik_dilaporkan_di_ringkasan() -> None:
    """Hitungan non-Inggris harus terlihat di laporan CLI, bukan senyap."""
    stats = PipelineStats(artikel_bukan_inggris=7)
    assert "bukan Inggris" in stats.ringkas()
    assert "7" in stats.ringkas()
