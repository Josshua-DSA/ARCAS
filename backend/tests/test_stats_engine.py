"""StatEngine multi-lag tests for the association workbench (Upgrade.md UI-05)."""

from datetime import date, timedelta

from backend.src.schema import DailySentiment, PriceRecord
from backend.src.stats.engine import StatEngine

D0 = date(2026, 7, 1)


def _demo_daily_prices():
    """Deterministic series: news on even days, alternating score and close."""
    prices = [
        PriceRecord(
            asset_id="XAU",
            date=D0 + timedelta(days=i),
            open=1.0,
            high=1.1,
            low=0.9,
            close=100.0 + i,
            adj_close=1.0,
            volume=1000.0,
        )
        for i in range(40)
    ]
    daily = [
        DailySentiment(
            asset_id="XAU",
            date=D0 + timedelta(days=i),
            n_articles=1 if i % 2 == 0 else 0,
            n_sources=1 if i % 2 == 0 else 0,
            has_news=i % 2 == 0,
            score_mean=(0.3 if i % 4 == 0 else -0.2) if i % 2 == 0 else None,
        )
        for i in range(40)
    ]
    return daily, prices


def test_frame_keeps_news_free_days_nan():
    """Merged frame keeps engine columns; news-free days stay NaN, not 0."""
    daily, prices = _demo_daily_prices()
    frame = StatEngine.frame_from_daily_prices(daily, prices)
    assert list(frame.columns) == ["date", "close", "score_mean"]
    assert len(frame) == 40
    assert int(frame["score_mean"].isna().sum()) == 20


def test_frame_from_empty_inputs_is_empty():
    assert StatEngine.frame_from_daily_prices([], []).empty


def test_spearman_lags_computed_live():
    """Live computation returns one result per lag 0..max_lag, metric=return."""
    daily, prices = _demo_daily_prices()
    frame = StatEngine.frame_from_daily_prices(daily, prices)
    out = StatEngine.compute_spearman_lags(frame, "XAU", max_lag=3)
    assert [r.lag for r in out] == [0, 1, 2, 3]
    assert all(r.market_metric == "return" for r in out)
    assert all(r.p_adjusted is not None for r in out)
    # Lag shifts consume observations: n_obs cannot grow with the lag.
    assert all(out[i].n_obs >= out[i + 1].n_obs for i in range(len(out) - 1))


def test_spearman_lags_empty_frame_returns_empty():
    frame = StatEngine.frame_from_daily_prices([], [])
    assert StatEngine.compute_spearman_lags(frame, "XAU", max_lag=2) == []
