"""Adapter Finnhub — berita pasar umum, forex, dan merger.

Endpoint: GET /api/v1/news?category={general|forex|merger}&token=KEY
Finnhub tidak punya pencarian kata kunci di endpoint ini, jadi relevansi
target ditentukan lewat filter kata kunci lokal (`keywords.py`).
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
from backend.src.collect.news_api.keywords import (
    TARGET_KEYWORDS,
    matches_target,
    score_relevance,
)

BASE = "https://finnhub.io/api/v1/news"

# Kategori yang relevan untuk tiap target universe.
TARGET_CATEGORIES: dict[str, tuple[str, ...]] = {
    "XAU": ("general", "forex", "merger"),
    "RATE_UST": ("general", "forex"),
    "SPX": ("general", "merger"),
}


class FinnhubAdapter:
    name = "finnhub"
    env_key = "FINNHUB_API_KEY"

    def __init__(self, client: NewsAPIClient | None = None, key: str | None = None) -> None:
        self.client = client or NewsAPIClient()
        self._key = key if key is not None else env(self.env_key)

    def is_configured(self) -> bool:
        return bool(self._key)

    # ---------------- internals ----------------

    def _raw_news(self, category: str) -> tuple[list[dict[str, Any]], float]:
        data, latency = self.client.get_json(
            BASE, {"category": category, "token": self._key}
        )
        if not isinstance(data, list):
            # Finnhub mengembalikan {"error": "..."} saat kunci salah
            msg = str(data)[:160] if not isinstance(data, dict) else str(data.get("error", data))[:160]
            raise ApiError(ApiStatus.UNAUTHORIZED, msg)
        return data, latency

    @staticmethod
    def _to_item(row: dict[str, Any], target: str) -> NewsItem:
        ts = row.get("datetime")
        published = (
            datetime.fromtimestamp(int(ts), tz=timezone.utc) if ts else None
        )
        return NewsItem(
            source=f"finnhub:{row.get('source', 'unknown')}",
            title=(row.get("headline") or "").strip(),
            url=row.get("url"),
            body=(row.get("summary") or "").strip() or None,
            published_at=published,
            query_target=target,
            payload={
                "finnhub_id": row.get("id"),
                "category": row.get("category"),
                "related": row.get("related"),
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
            data, latency = self._raw_news("general")
        except ApiError as exc:
            return HealthReport(
                provider=self.name, status=exc.status, detail=exc.detail
            )
        if not data:
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
            sample_size=len(data),
            sample_title=(data[0].get("headline") or "")[:80],
        )

    def fetch(self, target: str, limit: int = 50) -> list[NewsItem]:
        """Tarik berita relevan untuk satu target.

        Menggabungkan beberapa kategori lalu memfilter dengan kata kunci target.
        """
        if not self.is_configured():
            raise ApiError(ApiStatus.NO_KEY, f"{self.env_key} tidak diset")
        if target not in TARGET_KEYWORDS:
            raise ValueError(f"target di luar universe terkunci: {target}")

        seen: set[str] = set()
        scored: list[tuple[int, NewsItem]] = []

        for category in TARGET_CATEGORIES.get(target, ("general",)):
            rows, _ = self._raw_news(category)
            for row in rows:
                fid = str(row.get("id") or row.get("url") or "")
                if fid and fid in seen:
                    continue
                title = (row.get("headline") or "").strip()
                if not title:
                    continue
                haystack = f"{title} {row.get('summary') or ''}"
                if not matches_target(haystack, target):
                    continue
                seen.add(fid)
                scored.append((score_relevance(haystack, target), self._to_item(row, target)))

        # Berita paling relevan lebih dulu.
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]
