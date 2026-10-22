"""Adapter Marketaux — berita dengan entitas & sentimen bawaan vendor.

Endpoint: GET /v1/news/all
Catatan penting hasil uji: parameter `symbols=GC=F` / `XAUUSD` mengembalikan
0 hasil pada paket gratis. Yang bekerja adalah `countries=us` + `filter_entities`.
Jadi adapter memakai countries sebagai basis, lalu memfilter kata kunci lokal.
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

BASE = "https://api.marketaux.com/v1/news/all"


class MarketauxAdapter:
    name = "marketaux"
    env_key = "MARKETAUX_API_KEY"

    def __init__(self, client: NewsAPIClient | None = None, key: str | None = None) -> None:
        self.client = client or NewsAPIClient()
        self._key = key if key is not None else env(self.env_key)

    def is_configured(self) -> bool:
        return bool(self._key)

    # ---------------- internals ----------------

    def _query(self, target: str, limit: int) -> tuple[dict[str, Any], float]:
        params: dict[str, Any] = {
            "countries": "us",
            "filter_entities": "true",
            "language": "en",
            "limit": max(1, min(limit, 100)),
            "api_token": self._key,
        }
        data, latency = self.client.get_json(BASE, params)
        if not isinstance(data, dict):
            raise ApiError(ApiStatus.ERROR, f"respons tak terduga: {str(data)[:120]}")
        if "error" in data:
            err = data["error"]
            msg = err.get("message", "") if isinstance(err, dict) else str(err)
            status = ApiStatus.UNAUTHORIZED if "token" in msg.lower() or "auth" in msg.lower() else ApiStatus.ERROR
            raise ApiError(status, msg[:160])
        return data, latency

    @staticmethod
    def _to_item(row: dict[str, Any], target: str) -> NewsItem:
        published = None
        raw = row.get("published_at")
        if raw:
            try:
                published = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).astimezone(timezone.utc)
            except ValueError:
                published = None

        entities = row.get("entities") or []
        vendor_sentiment = None
        for ent in entities:
            if isinstance(ent, dict) and ent.get("sentiment_score") is not None:
                try:
                    vendor_sentiment = float(ent["sentiment_score"])
                except (TypeError, ValueError):
                    vendor_sentiment = None
                break

        return NewsItem(
            source=f"marketaux:{row.get('source', 'unknown')}",
            title=(row.get("title") or "").strip(),
            url=row.get("url"),
            body=(row.get("description") or row.get("snippet") or "").strip() or None,
            published_at=published,
            query_target=target,
            vendor_sentiment=vendor_sentiment,
            payload={
                "marketaux_uuid": row.get("uuid"),
                "entities": [
                    e.get("symbol") for e in entities if isinstance(e, dict)
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
        rows = data.get("data") or []
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

        data, _ = self._query(target, limit=100)
        rows = data.get("data") or []

        items: list[NewsItem] = []
        for row in rows:
            title = (row.get("title") or "").strip()
            if not title:
                continue
            haystack = f"{title} {row.get('description') or ''} {row.get('snippet') or ''}"
            if not matches_target(haystack, target):
                continue
            items.append(self._to_item(row, target))
            if len(items) >= limit:
                break
        return items
