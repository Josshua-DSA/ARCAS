"""Adapter Alpha Vantage NEWS_SENTIMENT.

Endpoint: GET /query?function=NEWS_SENTIMENT
Hasil uji: pada kunci gratis, endpoint ini mengembalikan pesan
"premium endpoint". Adapter mendeteksinya dan melaporkan `PREMIUM_ONLY`
alih-alih gagal senyap — supaya tidak dikira tidak ada berita.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.src.collect.news_api.base import (
    ApiStatus,
    HealthReport,
    NewsItem,
)
from backend.src.collect.news_api.client import ApiError, NewsAPIClient, env
from backend.src.collect.news_api.keywords import TARGET_KEYWORDS, matches_target

BASE = "https://www.alphavantage.co/query"

# Topik Alpha Vantage yang paling dekat dengan tiap target.
TARGET_TOPICS: dict[str, str] = {
    "XAU": "economy_macro",
    "RATE_UST": "economy_macro,interest_rate",
    "SPX": "financial_markets,earnings",
}


class AlphaVantageAdapter:
    name = "alphavantage"
    env_key = "ALPHAVANTAGE_API_KEY"

    def __init__(self, client: NewsAPIClient | None = None, key: str | None = None) -> None:
        self.client = client or NewsAPIClient()
        self._key = key if key is not None else env(self.env_key)

    def is_configured(self) -> bool:
        return bool(self._key)

    # ---------------- internals ----------------

    def _query(self, target: str, limit: int) -> tuple[dict[str, Any], float]:
        params: dict[str, Any] = {
            "function": "NEWS_SENTIMENT",
            "topics": TARGET_TOPICS.get(target, "economy_macro"),
            "limit": max(1, min(limit, 1000)),
            "apikey": self._key,
        }
        data, latency = self.client.get_json(BASE, params)
        if not isinstance(data, dict):
            raise ApiError(ApiStatus.ERROR, f"respons tak terduga: {str(data)[:120]}")

        # Alpha Vantage memakai 200 OK untuk pesan kuota/premium.
        for flag in ("Information", "Note"):
            if flag in data:
                msg = str(data[flag])
                status = (
                    ApiStatus.PREMIUM_ONLY
                    if "premium" in msg.lower()
                    else ApiStatus.RATE_LIMITED
                )
                raise ApiError(status, msg[:160])
        if "Error Message" in data:
            raise ApiError(ApiStatus.UNAUTHORIZED, str(data["Error Message"])[:160])
        return data, latency

    @staticmethod
    def _to_item(row: dict[str, Any], target: str) -> NewsItem:
        published = None
        raw = row.get("time_published")  # format: 20261021T131500
        if raw:
            try:
                published = datetime.strptime(str(raw), "%Y%m%dT%H%M%S").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                published = None

        vendor_sentiment = None
        try:
            vendor_sentiment = float(row["overall_sentiment_score"])
        except (KeyError, TypeError, ValueError):
            vendor_sentiment = None

        return NewsItem(
            source=f"alphavantage:{row.get('source', 'unknown')}",
            title=(row.get("title") or "").strip(),
            url=row.get("url"),
            body=(row.get("summary") or "").strip() or None,
            published_at=published,
            query_target=target,
            vendor_sentiment=vendor_sentiment,
            payload={
                "tickers": [
                    t.get("ticker") for t in (row.get("ticker_sentiment") or [])
                    if isinstance(t, dict)
                ][:10],
            },
        )

    # ---------------- public ----------------

    def probe(self) -> HealthReport:
        if not self.is_configured():
            return HealthReport(
                provider=self.name,
                status=ApiStatus.NO_KEY,
                detail=f"{self.env_key} tidak diset",
            )
        try:
            data, latency = self._query("SPX", limit=3)
        except ApiError as exc:
            return HealthReport(
                provider=self.name, status=exc.status, detail=exc.detail
            )
        rows = data.get("feed") or []
        if not rows:
            return HealthReport(
                provider=self.name,
                status=ApiStatus.EMPTY,
                detail="kunci valid, nol item",
                latency_ms=round(latency, 1),
            )
        return HealthReport(
            provider=self.name,
            status=ApiStatus.OK,
            detail="kunci valid",
            latency_ms=round(latency, 1),
            sample_size=len(rows),
            sample_title=(rows[0].get("title") or "")[:80],
        )

    def fetch(self, target: str, limit: int = 50) -> list[NewsItem]:
        if not self.is_configured():
            raise ApiError(ApiStatus.NO_KEY, f"{self.env_key} tidak diset")
        if target not in TARGET_KEYWORDS:
            raise ValueError(f"target di luar universe terkunci: {target}")

        data, _ = self._query(target, limit=limit * 2)
        rows = data.get("feed") or []

        items: list[NewsItem] = []
        for row in rows:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            haystack = f"{title} {row.get('summary') or ''}"
            if not matches_target(haystack, target):
                continue
            items.append(self._to_item(row, target))
            if len(items) >= limit:
                break
        return items
