"""Tanggal bursa harus terisi untuk SETIAP aset yang ditandai, bukan hanya query_target.

Regresi nyata: normalizer hanya menghitung tanggal untuk `raw.query_target`
(satu aset), sehingga tag untuk aset lain tersimpan dengan
effective_trading_date = NULL. Di data 2026-11-09: 227 dari 310 tag bolong
(73%), dan satu artikel yang sama bisa punya XAU NULL padahal SPX terisi.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from backend.src.normalize.cleaner import ArticleCleaner
from backend.src.schema import Article, Basis, Lang, RawArticle, TargetTag
from backend.src.store.db import Database

# Jumat 20:00 UTC == Sabtu 03:00 WIB. Masih sesi Jumat untuk ketiga aset.
JUMAT_MALAM = datetime(2026, 11, 6, 20, 0, tzinfo=timezone.utc)
# Senin 23:00 UTC: lewat cut-off 21:00 untuk SPX/RATE_UST -> efektif Selasa.
SENIN_MALAM = datetime(2026, 11, 9, 23, 0, tzinfo=timezone.utc)


def _raw(query_target: str | None = "SPX") -> RawArticle:
    return RawArticle(
        source="finnhub:headline:SPY",
        url="https://example.com/a",
        title="Gold slides as yields climb, equities retreat",
        body="Gold and equities both fell while Treasury yields rose.",
        published_at=JUMAT_MALAM,
        fetched_at=JUMAT_MALAM,
        query_target=query_target,
    )


def test_tanggal_dihitung_untuk_semua_aset_bukan_hanya_query_target() -> None:
    """query_target=SPX, tapi artikel juga menandai XAU dan RATE_UST."""
    article = ArticleCleaner.process_raw(_raw(query_target="SPX"))

    assert set(article.effective_trading_date) == {"XAU", "RATE_UST", "SPX"}


def test_tanpa_query_target_tetap_menghitung_semua_aset() -> None:
    """Sumber RSS tidak punya query_target; dulu peta tanggal kosong total."""
    article = ArticleCleaner.process_raw(_raw(query_target=None))

    assert set(article.effective_trading_date) == {"XAU", "RATE_UST", "SPX"}


def test_cut_off_berbeda_per_aset_dihormati() -> None:
    """Senin 23:00 UTC: XAU (24 jam) tetap Senin, SPX/RATE_UST geser ke Selasa."""
    raw = _raw(query_target="SPX")
    raw.published_at = SENIN_MALAM
    article = ArticleCleaner.process_raw(raw)

    assert article.effective_trading_date["XAU"] == date(2026, 11, 9)
    assert article.effective_trading_date["SPX"] == date(2026, 11, 10)
    assert article.effective_trading_date["RATE_UST"] == date(2026, 11, 10)


def test_akhir_pekan_digeser_ke_senin() -> None:
    """Sabtu 12:00 UTC -> Senin untuk ketiga aset."""
    raw = _raw()
    raw.published_at = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)
    article = ArticleCleaner.process_raw(raw)

    assert article.effective_trading_date["XAU"] == date(2026, 11, 9)
    assert article.effective_trading_date["SPX"] == date(2026, 11, 9)


@pytest.fixture()
def db(temp_db: Database) -> Database:
    """DB sementara + satu artikel, karena article_targets punya FK ke articles."""
    temp_db.save_article(
        Article(
            article_id="art-1",
            source="finnhub:headline:SPY",
            url="https://example.com/a",
            title="Gold slides as yields climb",
            body=None,
            language=Lang.EN,
            published_at=JUMAT_MALAM,
            fetched_at=JUMAT_MALAM,
        )
    )
    return temp_db


def test_penulisan_tag_memakai_tanggal_per_aset(db: Database) -> None:
    """save_article_targets menyimpan tanggal sesuai asset_id tag, bukan yang pertama."""
    tags = [
        TargetTag(asset_id="XAU", basis=Basis.EXPLICIT, matched_text="gold"),
        TargetTag(asset_id="SPX", basis=Basis.MACRO_FACTOR, matched_text="equities"),
        TargetTag(asset_id="RATE_UST", basis=Basis.MACRO_FACTOR, matched_text="yields"),
    ]
    tanggal = {
        "XAU": date(2026, 11, 9),
        "SPX": date(2026, 11, 10),
        "RATE_UST": date(2026, 11, 10),
    }
    db.save_article_targets("art-1", tags, tanggal)

    tersimpan = {
        r["asset_id"]: r["effective_trading_date"]
        for r in db.query_article_targets("art-1")
    }
    assert tersimpan == {
        "XAU": "2026-11-09",
        "SPX": "2026-11-10",
        "RATE_UST": "2026-11-10",
    }


def test_tag_tanpa_tanggal_tidak_disimpan_null(db: Database) -> None:
    """Aset yang tidak ada di peta tanggal harus ditolak, bukan disimpan NULL.

    Inilah sumber 227 baris bolong: penulisan meloloskan asset_id yang tidak
    punya entri tanggal, lalu menyimpan NULL tanpa suara.
    """
    tags = [TargetTag(asset_id="OIL", basis=Basis.EXPLICIT, matched_text="minyak")]
    with pytest.raises(ValueError):
        db.save_article_targets("art-x", tags, {"SPX": date(2026, 11, 9)})

    assert db.query_article_targets("art-x") == []
