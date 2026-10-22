"""Test untuk modul news_api (identifikasi API + adapter)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from backend.src.collect.news_api.base import ApiStatus, NewsItem
from backend.src.collect.news_api.client import ApiError, NewsAPIClient
from backend.src.collect.news_api.keywords import (
    TARGET_KEYWORDS,
    count_hits,
    matches_target,
    score_relevance,
)

# ==========================================================
# keywords — inti kualitas relevansi
# ==========================================================

def test_word_boundary_blocks_substring_false_positive():
    """Kata kunci "war" tidak boleh cocok di "software"/"award"/"hardware".

    Regresi: sebelumnya "war" cocok di "software" dan meloloskan berita NBA.
    """
    for text in (
        "Software stocks rally",
        "He won an award",
        "Hardware demand grows",
        "Moving toward the exit",
    ):
        assert not matches_target(text, "XAU"), text


def test_macro_only_news_rejected_when_specific_required():
    """Berita yang hanya menyebut kata makro tidak cukup untuk target."""
    assert not matches_target("Inflation eased last month", "XAU")
    assert not matches_target("Inflation eased last month", "SPX")


def test_specific_keyword_accepted():
    assert matches_target("Gold prices climb as real yields fall", "XAU")
    assert matches_target("Treasury yields jump after Fed signals", "RATE_UST")
    assert matches_target("S&P 500 hits record as earnings beat", "SPX")


def test_hyphen_and_space_variants():
    """"safe haven" harus cocok juga dengan "safe-haven"."""
    assert matches_target("Gold is a safe-haven asset", "XAU")
    assert matches_target("Gold is a safe haven asset", "XAU")


def test_score_ranks_specific_above_macro():
    specific = score_relevance("Gold prices climb as real yields fall", "XAU")
    macro = score_relevance("Inflation eased last month", "XAU")
    assert specific > macro


def test_all_locked_targets_have_keywords():
    for target in ("XAU", "RATE_UST", "SPX"):
        assert TARGET_KEYWORDS[target], f"kata kunci kosong untuk {target}"


def test_count_hits_empty_text():
    assert count_hits("", TARGET_KEYWORDS["XAU"]) == 0


# ==========================================================
# NewsItem -> RawArticle
# ==========================================================

def test_news_item_to_raw_article():
    item = NewsItem(
        source="finnhub:reuters",
        title="Gold rises",
        url="https://example.com/1",
        body="gold up",
        published_at=datetime(2026, 10, 20, tzinfo=timezone.utc),
        query_target="XAU",
    )
    raw = item.to_raw_article()
    assert raw.source == "finnhub:reuters"
    assert raw.title == "Gold rises"
    assert raw.query_target == "XAU"
    assert raw.fetched_at.tzinfo is not None, "fetched_at harus timezone-aware"


# ==========================================================
# Client — klasifikasi error
# ==========================================================

def test_client_masks_secrets_in_params():
    masked = NewsAPIClient._mask({"token": "abc", "category": "general", "api_token": "x"})
    assert masked["token"] == "***"
    assert masked["api_token"] == "***"
    assert masked["category"] == "general"


def test_api_error_carries_status():
    err = ApiError(ApiStatus.NO_KEY, "kunci kosong")
    assert err.status is ApiStatus.NO_KEY
    assert "kosong" in err.detail


# ==========================================================
# Adapter — perilaku saat kunci tidak ada (tanpa jaringan)
# ==========================================================

def test_finnhub_without_key_is_not_configured():
    from backend.src.collect.news_api.finnhub import FinnhubAdapter

    adapter = FinnhubAdapter(key="")
    assert adapter.is_configured() is False
    report = adapter.probe()
    assert report.status is ApiStatus.NO_KEY
    assert report.usable is False


def test_adapter_rejects_target_outside_universe():
    from backend.src.collect.news_api.finnhub import FinnhubAdapter

    adapter = FinnhubAdapter(key="dummy")
    with pytest.raises(ValueError, match="di luar universe"):
        adapter.fetch("BTC", limit=1)


def test_marketaux_without_key_is_not_configured():
    from backend.src.collect.news_api.marketaux import MarketauxAdapter

    adapter = MarketauxAdapter(key="")
    assert adapter.probe().status is ApiStatus.NO_KEY


def test_alphavantage_without_key_is_not_configured():
    from backend.src.collect.news_api.alphavantage import AlphaVantageAdapter

    adapter = AlphaVantageAdapter(key="")
    assert adapter.probe().status is ApiStatus.NO_KEY
