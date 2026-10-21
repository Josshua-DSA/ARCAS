"""Price data collector for the 3 core locked assets (XAU, RATE_UST, SPX).

Sumber data nyata: Yahoo Finance chart API (tanpa dependensi `yfinance`).
Data sintetis HANYA dihasilkan lewat `fetch_prices_synthetic()` yang harus
dipanggil eksplisit — tidak pernah lagi sebagai fallback senyap, karena itu
membuat pipeline tampak berjalan padahal isinya angka acak.
"""

from __future__ import annotations

import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from backend.src.schema import PriceRecord

CORE_ASSETS = ("XAU", "RATE_UST", "SPX")

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
DEFAULT_UA = "Mozilla/5.0 (compatible; FInews/0.6)"


class PriceFetchError(RuntimeError):
    """Gagal mengambil harga nyata dari penyedia.

    Dilempar alih-alih mengembalikan data sintetis, supaya kegagalan sumber
    terlihat dan bisa dicatat ke `source_health`.
    """


@dataclass(slots=True)
class FetchResult:
    """Hasil satu penarikan harga, termasuk asal datanya."""

    asset_id: str
    records: list[PriceRecord]
    source: str  # "yahoo" | "synthetic"
    note: str = ""

    @property
    def is_real(self) -> bool:
        return self.source == "yahoo"


class PriceCollector:
    """Fetches daily prices for core locked universe assets."""

    def __init__(
        self,
        asset_master_path: Path | str = Path("data/universe/asset_master.csv"),
        timeout: float = 20.0,
        max_retries: int = 2,
        backoff_base: float = 1.5,
    ) -> None:
        self.asset_master_path = Path(asset_master_path)
        self.ticker_map: dict[str, str] = {}
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.last_errors: dict[str, str] = {}
        self._load_asset_master()

    def _load_asset_master(self) -> None:
        if self.asset_master_path.exists():
            with open(self.asset_master_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("active", "True").lower() not in ("true", "1"):
                        continue
                    self.ticker_map[row["asset_id"]] = row["price_ticker"]

    # ---------------- jaringan ----------------

    def _yahoo_daily(self, ticker: str, start_date: date, end_date: date) -> list[PriceRecord]:
        """Ambil OHLC harian dari Yahoo chart API.

        `period1`/`period2` memakai epoch detik. Hasil kosong → PriceFetchError.
        """
        p1 = int(datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc).timestamp())
        p2 = int(
            datetime.combine(
                end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc
            ).timestamp()
        )
        params = urllib.parse.urlencode(
            {"period1": p1, "period2": p2, "interval": "1d", "events": "div,splits"}
        )
        url = f"{YAHOO_CHART.format(ticker=urllib.parse.quote(ticker))}?{params}"

        last_err: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": DEFAULT_UA})
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                return self._parse_yahoo(data, ticker)
            except urllib.error.HTTPError as exc:
                last_err = exc
                if exc.code in (401, 403, 404):
                    break
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                last_err = exc
            if attempt < self.max_retries:
                time.sleep(self.backoff_base ** attempt)

        raise PriceFetchError(f"Yahoo gagal untuk {ticker}: {last_err}")

    @staticmethod
    def _parse_yahoo(data: dict, ticker: str) -> list[PriceRecord]:
        chart = data.get("chart") or {}
        if chart.get("error"):
            raise PriceFetchError(f"Yahoo error untuk {ticker}: {chart['error']}")
        results = chart.get("result") or []
        if not results:
            raise PriceFetchError(f"Yahoo mengembalikan hasil kosong untuk {ticker}")

        result = results[0]
        timestamps = result.get("timestamp") or []
        indicators = result.get("indicators") or {}
        quote = (indicators.get("quote") or [{}])[0]
        adj = (indicators.get("adjclose") or [{}])[0].get("adjclose")

        closes = quote.get("close") or []
        opens = quote.get("open") or []
        highs = quote.get("high") or []
        lows = quote.get("low") or []
        volumes = quote.get("volume") or []

        def pick(seq: list, idx: int, fallback: float) -> float:
            if idx < len(seq) and seq[idx] is not None:
                return float(seq[idx])
            return fallback

        records: list[PriceRecord] = []
        for idx, ts in enumerate(timestamps):
            if idx >= len(closes) or closes[idx] is None:
                continue  # hari libur / bar tidak lengkap
            close = float(closes[idx])
            day = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            records.append(
                PriceRecord(
                    asset_id="",  # diisi pemanggil
                    date=day,
                    open=pick(opens, idx, close),
                    high=pick(highs, idx, close),
                    low=pick(lows, idx, close),
                    close=close,
                    adj_close=(
                        float(adj[idx])
                        if adj and idx < len(adj) and adj[idx] is not None
                        else close
                    ),
                    volume=pick(volumes, idx, 0.0),
                )
            )
        if not records:
            raise PriceFetchError(f"Yahoo tidak memberi bar valid untuk {ticker}")
        return records

    # ---------------- API publik ----------------

    def fetch_prices(
        self, asset_id: str, start_date: date, end_date: date
    ) -> list[PriceRecord]:
        """Ambil harga nyata. Melempar `PriceFetchError` bila gagal.

        Tidak ada fallback ke data sintetis. Pemanggil yang memutuskan mau
        memakai `fetch_prices_synthetic()` atau tidak.
        """
        ticker = self.ticker_map.get(asset_id)
        if not ticker:
            raise ValueError(f"Unknown asset_id: {asset_id}")

        records = self._yahoo_daily(ticker, start_date, end_date)
        for r in records:
            r.asset_id = asset_id
        return records

    def fetch_with_meta(
        self, asset_id: str, start_date: date, end_date: date
    ) -> FetchResult:
        """Seperti `fetch_prices`, tapi mengembalikan asal data secara eksplisit."""
        records = self.fetch_prices(asset_id, start_date, end_date)
        return FetchResult(asset_id=asset_id, records=records, source="yahoo")

    def fetch_universe_prices(
        self, start_date: date, end_date: date
    ) -> dict[str, list[PriceRecord]]:
        """Fetches real prices for all active core assets.

        Satu aset gagal tidak menghentikan yang lain; kegagalan dicatat di
        `last_errors`. Bila SEMUA gagal, `PriceFetchError` dilempar.
        """
        out: dict[str, list[PriceRecord]] = {}
        errors: dict[str, str] = {}
        for asset_id in CORE_ASSETS:
            if asset_id not in self.ticker_map:
                continue
            try:
                out[asset_id] = self.fetch_prices(asset_id, start_date, end_date)
            except (PriceFetchError, ValueError) as exc:
                errors[asset_id] = str(exc)
        self.last_errors = errors
        if not out and errors:
            raise PriceFetchError(f"semua aset gagal: {errors}")
        return out

    # ---------------- sintetis (eksplisit) ----------------

    def fetch_prices_synthetic(
        self,
        asset_id: str,
        start_date: date,
        end_date: date,
        base_price: float = 100.0,
        volatility: float = 0.015,
    ) -> list[PriceRecord]:
        """Generates synthetic daily price series.

        HANYA untuk test/offline simulation. Tidak pernah dipanggil otomatis.
        """
        records: list[PriceRecord] = []
        curr = start_date
        price = base_price

        np.random.seed(abs(hash(asset_id)) % (2**31))

        while curr <= end_date:
            # All 3 core assets halt on weekends (CME/CBOE/SNP calendars)
            if curr.weekday() in (5, 6):
                curr += timedelta(days=1)
                continue

            ret = float(np.random.normal(0.0005, volatility))
            close = max(1.0, price * (1.0 + ret))
            high = close * (1.0 + abs(float(np.random.normal(0, 0.005))))
            low = close * (1.0 - abs(float(np.random.normal(0, 0.005))))
            open_p = (price + close) / 2.0
            volume = float(np.random.lognormal(12, 1))

            records.append(
                PriceRecord(
                    asset_id=asset_id,
                    date=curr,
                    open=round(open_p, 4),
                    high=round(high, 4),
                    low=round(low, 4),
                    close=round(close, 4),
                    adj_close=round(close, 4),
                    volume=round(volume, 0),
                )
            )

            price = close
            curr += timedelta(days=1)

        return records
