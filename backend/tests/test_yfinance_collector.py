"""Uji `PriceCollector` (backend/src/collect/yfinance_collector.py).

Modul ini sebelumnya **nol test**. Yang diuji di sini adalah bagian yang tidak
butuh jaringan: pemuatan peta ticker, parsing respons Yahoo (termasuk bar
tidak lengkap dan field opsional), dan pagar penting bahwa kegagalan sumber
**tidak** diam-diam diganti data sintetis.

Pesan desain modul ini patut dijaga: `fetch_prices` melempar `PriceFetchError`
alih-alih mengembalikan angka acak, supaya pipeline tidak tampak berjalan
padahal isinya data palsu. Test di bawah mengunci perilaku itu.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone

import pytest

from backend.src.collect.yfinance_collector import (
    CORE_ASSETS,
    FetchResult,
    PriceCollector,
    PriceFetchError,
)


@pytest.fixture
def collector(tmp_path):
    """Kolektor dengan peta ticker buatan sendiri (tidak menyentuh data repo)."""
    master = tmp_path / "asset_master.csv"
    master.write_text(
        "asset_id,price_ticker,active\n"
        "XAU,GC=F,True\n"
        "RATE_UST,^TNX,True\n"
        "SPX,^GSPC,True\n"
        "NONAKTIF,XXX,False\n",
        encoding="utf-8",
    )
    return PriceCollector(asset_master_path=master, max_retries=0)


def _yahoo_payload(timestamps: list[int], closes: list, **overrides) -> dict:
    quote = {
        "open": overrides.get("open", closes),
        "high": overrides.get("high", closes),
        "low": overrides.get("low", closes),
        "close": closes,
        "volume": overrides.get("volume", [1000] * len(closes)),
    }
    return {
        "chart": {
            "result": [
                {
                    "timestamp": timestamps,
                    "indicators": {
                        "quote": [quote],
                        "adjclose": [{"adjclose": overrides.get("adjclose", closes)}],
                    },
                }
            ],
            "error": None,
        }
    }


# ---------------------------------------------------------------------------
# Pemuatan asset master
# ---------------------------------------------------------------------------


def test_ticker_map_loads_only_active_assets(collector):
    assert collector.ticker_map["XAU"] == "GC=F"
    assert "NONAKTIF" not in collector.ticker_map


def test_missing_asset_master_is_not_fatal(tmp_path):
    """Tanpa file master, kolektor tetap dibuat; fetch yang akan menolak."""
    c = PriceCollector(asset_master_path=tmp_path / "tidak_ada.csv")
    assert c.ticker_map == {}


def test_fetch_unknown_asset_raises_value_error(collector):
    with pytest.raises(ValueError, match="Unknown asset_id"):
        collector.fetch_prices("TIDAK_ADA", date(2026, 1, 1), date(2026, 1, 5))


# ---------------------------------------------------------------------------
# Parsing respons Yahoo
# ---------------------------------------------------------------------------


def test_parse_yahoo_produces_records_with_utc_dates():
    ts = [
        int(datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 1, 6, tzinfo=timezone.utc).timestamp()),
    ]
    records = PriceCollector._parse_yahoo(_yahoo_payload(ts, [100.0, 101.5]), "GC=F")

    assert len(records) == 2
    assert records[0].date == date(2026, 1, 5)
    assert records[1].date == date(2026, 1, 6)
    assert records[0].close == 100.0
    assert records[1].close == 101.5


def test_parse_yahoo_skips_days_with_null_close():
    """Hari libur / bar tidak lengkap harus dilewati, bukan jadi 0."""
    ts = [
        int(datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 1, 6, tzinfo=timezone.utc).timestamp()),
        int(datetime(2026, 1, 7, tzinfo=timezone.utc).timestamp()),
    ]
    records = PriceCollector._parse_yahoo(_yahoo_payload(ts, [100.0, None, 102.0]), "GC=F")

    assert len(records) == 2
    assert [r.date for r in records] == [date(2026, 1, 5), date(2026, 1, 7)]


def test_parse_yahoo_falls_back_to_close_for_missing_ohlc():
    """Bila open/high/low None, pakai close -- jangan hasilkan None."""
    ts = [int(datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp())]
    payload = _yahoo_payload(
        ts, [100.0], open=[None], high=[None], low=[None], volume=[None]
    )
    records = PriceCollector._parse_yahoo(payload, "GC=F")

    rec = records[0]
    assert rec.open == 100.0
    assert rec.high == 100.0
    assert rec.low == 100.0
    assert rec.volume == 0.0


def test_parse_yahoo_uses_adjclose_when_present():
    ts = [int(datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp())]
    payload = _yahoo_payload(ts, [100.0], adjclose=[99.5])
    assert PriceCollector._parse_yahoo(payload, "GC=F")[0].adj_close == 99.5


def test_parse_yahoo_raises_on_error_payload():
    with pytest.raises(PriceFetchError, match="Yahoo error"):
        PriceCollector._parse_yahoo({"chart": {"error": "Not Found", "result": None}}, "GC=F")


def test_parse_yahoo_raises_on_empty_result():
    with pytest.raises(PriceFetchError, match="hasil kosong"):
        PriceCollector._parse_yahoo({"chart": {"result": [], "error": None}}, "GC=F")


def test_parse_yahoo_raises_when_no_valid_bar():
    """Timestamp ada tapi semua close null -> tidak boleh mengembalikan []."""
    ts = [int(datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp())]
    with pytest.raises(PriceFetchError, match="bar valid"):
        PriceCollector._parse_yahoo(_yahoo_payload(ts, [None]), "GC=F")


# ---------------------------------------------------------------------------
# Pagar: gagal = error, bukan data sintetis
# ---------------------------------------------------------------------------


def test_fetch_failure_raises_instead_of_returning_synthetic(collector, monkeypatch):
    """Kegagalan jaringan tidak boleh diam-diam jadi data sintetis."""

    def boom(*_a, **_k):
        raise PriceFetchError("Yahoo gagal untuk GC=F: simulasi")

    monkeypatch.setattr(collector, "_yahoo_daily", boom)

    with pytest.raises(PriceFetchError):
        collector.fetch_prices("XAU", date(2026, 1, 1), date(2026, 1, 5))


def test_fetch_universe_continues_when_one_asset_fails(collector, monkeypatch):
    """Satu aset gagal tidak menghentikan yang lain; error dicatat."""
    from backend.src.schema import PriceRecord

    def fake(self, ticker, start, end):
        if ticker == "^TNX":
            raise PriceFetchError("gagal")
        return [
            PriceRecord(
                asset_id="",
                date=date(2026, 1, 5),
                open=1.0,
                high=1.0,
                low=1.0,
                close=1.0,
                adj_close=1.0,
                volume=0.0,
            )
        ]

    monkeypatch.setattr(PriceCollector, "_yahoo_daily", fake)
    out = collector.fetch_universe_prices(date(2026, 1, 1), date(2026, 1, 5))

    assert set(out) == {"XAU", "SPX"}
    assert "RATE_UST" in collector.last_errors


def test_fetch_universe_raises_only_when_all_fail(collector, monkeypatch):
    def boom(*_a, **_k):
        raise PriceFetchError("semua mati")

    monkeypatch.setattr(PriceCollector, "_yahoo_daily", boom)

    with pytest.raises(PriceFetchError, match="semua aset gagal"):
        collector.fetch_universe_prices(date(2026, 1, 1), date(2026, 1, 5))


def test_fetch_with_meta_marks_source_as_yahoo(collector, monkeypatch):
    from backend.src.schema import PriceRecord

    monkeypatch.setattr(
        PriceCollector,
        "_yahoo_daily",
        lambda self, t, s, e: [
            PriceRecord(
                asset_id="",
                date=date(2026, 1, 5),
                open=1.0,
                high=1.0,
                low=1.0,
                close=1.0,
                adj_close=1.0,
                volume=0.0,
            )
        ],
    )
    result = collector.fetch_with_meta("XAU", date(2026, 1, 1), date(2026, 1, 5))

    assert isinstance(result, FetchResult)
    assert result.is_real is True
    assert result.source == "yahoo"


# ---------------------------------------------------------------------------
# Sintetis hanya eksplisit
# ---------------------------------------------------------------------------


def test_synthetic_is_deterministic_per_asset(collector):
    a = collector.fetch_prices_synthetic("XAU", date(2026, 1, 1), date(2026, 1, 20))
    b = collector.fetch_prices_synthetic("XAU", date(2026, 1, 1), date(2026, 1, 20))
    assert [r.close for r in a] == [r.close for r in b]


def test_synthetic_skips_weekends(collector):
    records = collector.fetch_prices_synthetic("XAU", date(2026, 1, 1), date(2026, 1, 31))
    assert records, "harus ada bar"
    assert all(r.date.weekday() < 5 for r in records)
    assert all(r.close > 0 for r in records)


def test_core_assets_are_the_locked_universe():
    assert CORE_ASSETS == ("XAU", "RATE_UST", "SPX")


def test_parse_yahoo_json_roundtrip():
    """Payload hasil json.loads (bukan dict langsung) juga harus terbaca."""
    ts = [int(datetime(2026, 1, 5, tzinfo=timezone.utc).timestamp())]
    payload = json.loads(json.dumps(_yahoo_payload(ts, [100.0])))
    assert len(PriceCollector._parse_yahoo(payload, "GC=F")) == 1
