"""Test untuk CRUD tabel berita (K-3) dan kolektor RSS."""

from __future__ import annotations

import tempfile
from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from backend.src.schema import (
    Article,
    ArticleSentiment,
    Basis,
    Lang,
    ModelProbs,
    RawArticle,
    TargetTag,
)
from backend.src.store.db import Database


@pytest.fixture()
def db() -> Database:
    path = Path(tempfile.mkdtemp()) / "test.db"
    database = Database(path)
    database.init_schema()
    return database


def _raw(**over) -> RawArticle:
    base = dict(
        source="finnhub:reuters",
        url="https://example.com/1",
        title="Gold rises",
        body="gold up",
        published_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        query_target="XAU",
    )
    base.update(over)
    return RawArticle(**base)


def _article(article_id: str = "abc123", **over) -> Article:
    base = dict(
        article_id=article_id,
        source="finnhub:reuters",
        url="https://example.com/1",
        title="Gold rises",
        body="gold up",
        language=Lang.EN,
        published_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        market_relevant=True,
    )
    base.update(over)
    return Article(**base)


# ==========================================================
# raw_articles
# ==========================================================

def test_save_raw_article_returns_id(db: Database):
    raw_id = db.save_raw_article(_raw())
    assert raw_id > 0
    assert db.count_raw_articles() == 1


def test_save_raw_article_dedupes_by_url(db: Database):
    first = db.save_raw_article(_raw())
    second = db.save_raw_article(_raw())  # identik
    assert first == second
    assert db.count_raw_articles() == 1


def test_save_raw_article_dedupes_by_title_without_url(db: Database):
    db.save_raw_article(_raw(url=None))
    db.save_raw_article(_raw(url=None))
    assert db.count_raw_articles() == 1


def test_save_raw_articles_bulk_counts_only_new(db: Database):
    rows = [(_raw(url=f"https://example.com/{i}", title=f"Gold {i}"), None) for i in range(5)]
    assert db.save_raw_articles(rows) == 5
    # run kedua: semua duplikat
    assert db.save_raw_articles(rows) == 0
    assert db.count_raw_articles() == 5


def test_query_raw_articles_filters_by_source(db: Database):
    db.save_raw_article(_raw(source="finnhub:reuters", url="https://a/1"))
    db.save_raw_article(_raw(source="rss:fed", url="https://a/2"))
    assert len(db.query_raw_articles(source="finnhub")) == 1
    assert len(db.query_raw_articles(source="rss")) == 1


# ==========================================================
# articles
# ==========================================================

def test_save_and_get_article(db: Database):
    db.save_article(_article())
    assert db.article_exists("abc123")
    row = db.get_article("abc123")
    assert row is not None
    assert row["language"] == "en"
    assert row["market_relevant"] == 1


def test_get_missing_article_returns_none(db: Database):
    assert db.get_article("nope") is None
    assert db.article_exists("nope") is False


def test_save_articles_bulk(db: Database):
    arts = [_article(article_id=f"id{i}", url=f"https://a/{i}") for i in range(3)]
    assert db.save_articles(arts) == 3
    assert db.count_articles() == 3


# ==========================================================
# article_targets
# ==========================================================

def test_save_article_targets_and_query(db: Database):
    db.save_article(_article())
    tags = [
        TargetTag(asset_id="XAU", basis=Basis.EXPLICIT, matched_text="gold"),
        TargetTag(asset_id="SPX", basis=Basis.SECTOR_INFERRED, matched_text="market"),
    ]
    assert db.save_article_targets("abc123", tags, {"XAU": date(2026, 10, 21)}) == 2

    rows = db.query_article_targets("abc123")
    assert len(rows) == 2
    xau = next(r for r in rows if r["asset_id"] == "XAU")
    assert xau["effective_trading_date"] == "2026-10-21"
    assert xau["basis"] == "explicit"


def test_query_articles_by_target_joins_articles(db: Database):
    db.save_article(_article())
    db.save_article_targets(
        "abc123", [TargetTag(asset_id="XAU", basis=Basis.EXPLICIT)]
    )
    rows = db.query_articles_by_target("XAU")
    assert len(rows) == 1
    assert rows[0]["title"] == "Gold rises"
    assert db.query_articles_by_target("SPX") == []


# ==========================================================
# sentiments
# ==========================================================

def test_save_sentiment_one_row_per_model(db: Database):
    db.save_article(_article())
    sentiment = ArticleSentiment(
        article_id="abc123",
        tone="positive",
        score=0.5,
        probs=[
            ModelProbs(model="tfidf_lr", p_pos=0.6, p_neu=0.3, p_neg=0.1, model_version="v1"),
            ModelProbs(model="finbert", p_pos=0.5, p_neu=0.4, p_neg=0.1, model_version="v2"),
        ],
    )
    db.save_sentiment(sentiment)
    rows = db.query_sentiments("abc123")
    assert len(rows) == 2
    assert {r["model"] for r in rows} == {"tfidf_lr", "finbert"}


# ==========================================================
# labels
# ==========================================================

def test_save_and_query_labels(db: Database):
    db.save_label("abc123", "XAU", "josh", "positive")
    db.save_label("abc123", "XAU", "dina", "neutral")
    assert db.count_labels() == 2
    assert len(db.query_labels(asset_id="XAU")) == 2
    assert len(db.query_labels(annotator="josh")) == 1


def test_save_labels_bulk(db: Database):
    rows = [
        {"article_id": f"a{i}", "asset_id": "XAU", "annotator": "josh", "label": "positive"}
        for i in range(4)
    ]
    assert db.save_labels(rows) == 4
    assert db.count_labels() == 4


# ==========================================================
# RSS collector — parsing tanpa jaringan
# ==========================================================

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>Gold climbs as real yields fall</title>
    <link>https://example.com/gold</link>
    <description>Gold rose on Friday.</description>
    <pubDate>Mon, 20 Oct 2026 10:00:00 GMT</pubDate>
  </item>
</channel></rss>"""

ATOM_SAMPLE = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Treasury yields jump</title>
    <link href="https://example.com/yields"/>
    <summary>Yields rose after Fed comments.</summary>
    <updated>2026-10-20T10:00:00Z</updated>
  </entry>
</feed>"""


def test_rss_parse_rss20():
    from backend.src.collect.rss_collector import RSSCollector

    rows = RSSCollector._parse(RSS_SAMPLE)
    assert len(rows) == 1
    assert rows[0]["title"] == "Gold climbs as real yields fall"
    assert rows[0]["link"] == "https://example.com/gold"


def test_rss_parse_atom():
    from backend.src.collect.rss_collector import RSSCollector

    rows = RSSCollector._parse(ATOM_SAMPLE)
    assert len(rows) == 1
    assert rows[0]["title"] == "Treasury yields jump"
    assert rows[0]["link"] == "https://example.com/yields"


def test_rss_parse_invalid_xml_raises():
    from backend.src.collect.news_api.client import ApiError
    from backend.src.collect.rss_collector import RSSCollector

    with pytest.raises(ApiError):
        RSSCollector._parse("<not valid")


def test_rss_parse_date_formats():
    from backend.src.collect.rss_collector import _parse_date

    assert _parse_date("Mon, 20 Oct 2026 10:00:00 GMT") is not None
    assert _parse_date("2026-10-20T10:00:00Z") is not None
    assert _parse_date(None) is None
    assert _parse_date("bukan tanggal") is None
