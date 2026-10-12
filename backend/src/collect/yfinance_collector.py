"""Price data collector for the 3 locked assets (XAU/RATE_UST/SPX)."""

import csv
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
import numpy as np

from backend.src.schema import PriceRecord


class PriceCollector:
    """Fetches daily prices for locked universe assets."""

    def __init__(self, asset_master_path: Path | str = Path("data/universe/asset_master.csv")):
        self.asset_master_path = Path(asset_master_path)
        self.ticker_map: dict[str, str] = {}
        self._load_asset_master()

    def _load_asset_master(self) -> None:
        if self.asset_master_path.exists():
            with open(self.asset_master_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self.ticker_map[row["asset_id"]] = row["price_ticker"]

    def fetch_prices_synthetic(
        self,
        asset_id: str,
        start_date: date,
        end_date: date,
        base_price: float = 100.0,
        volatility: float = 0.015,
    ) -> list[PriceRecord]:
        """
        Generates realistic synthetic daily price series for testing or offline simulations.
        """
        records: list[PriceRecord] = []
        curr = start_date
        price = base_price

        np.random.seed(abs(hash(asset_id)) % (2**31))

        while curr <= end_date:
            # Skip weekend (semua 3 target ikut kalender bursa)
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

    def fetch_prices(
        self, asset_id: str, start_date: date, end_date: date
    ) -> list[PriceRecord]:
        """
        Fetches prices via yfinance if available, otherwise falls back to synthetic data.
        """
        ticker = self.ticker_map.get(asset_id)
        if not ticker:
            raise ValueError(f"Unknown asset_id: {asset_id}")

        try:
            import yfinance as yf  # type: ignore

            df = yf.download(ticker, start=start_date.isoformat(), end=end_date.isoformat(), progress=False)
            if df.empty:
                return self.fetch_prices_synthetic(asset_id, start_date, end_date)

            records: list[PriceRecord] = []
            for dt, row in df.iterrows():
                d = dt.date() if hasattr(dt, "date") else start_date
                records.append(
                    PriceRecord(
                        asset_id=asset_id,
                        date=d,
                        open=float(row["Open"]),
                        high=float(row["High"]),
                        low=float(row["Low"]),
                        close=float(row["Close"]),
                        adj_close=float(row.get("Adj Close", row["Close"])),
                        volume=float(row.get("Volume", 0.0)),
                    )
                )
            return records
        except Exception:
            # Offline or network fallback
            return self.fetch_prices_synthetic(asset_id, start_date, end_date)
