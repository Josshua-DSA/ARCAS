"""Kolektor RSS/Atom — tanpa dependensi `feedparser`.

Memakai `xml.etree.ElementTree` dari stdlib. Mendukung RSS 2.0 (`<item>`) dan
Atom (`<entry>`). Feed yang mati dilaporkan sebagai status, bukan exception
yang menghentikan pipeline (RULES: kegagalan sumber dicatat).
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from backend.src.collect.news_api.base import ApiStatus, HealthReport, NewsItem
from backend.src.collect.news_api.client import ApiError, NewsAPIClient
from backend.src.collect.news_api.keywords import TARGET_KEYWORDS, matches_target, score_relevance

# Feed yang sudah diverifikasi hidup (lihat AUDIT: kitco 404, yahoo rss 404).
# CATATAN: investing `news_285` BUKAN komoditas (isinya saham/bitcoin).
# Yang benar untuk emas: `commodities.rss` (analisis) dan `news_11.rss` (berita).
FEEDS: dict[str, list[dict[str, str]]] = {
    "XAU": [
        {
            "name": "investing_commodities_news",
            "url": "https://www.investing.com/rss/news_11.rss",
        },
        {
            "name": "investing_commodities_analysis",
            "url": "https://www.investing.com/rss/commodities.rss",
        },
        {
            "name": "marketwatch_top",
            "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        },
    ],
    "RATE_UST": [
        {
            "name": "fed_press",
            "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        },
        {
            "name": "investing_commodities_news",
            "url": "https://www.investing.com/rss/news_11.rss",
        },
    ],
    "SPX": [
        {
            "name": "marketwatch_top",
            "url": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
        },
        {
            "name": "bbc_business",
            "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
        },
    ],
}

_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
    "content": "http://purl.org/rss/1.0/modules/content/",
}

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(text: str | None) -> str:
    """Buang tag HTML dan rapikan spasi."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", _TAG_RE.sub(" ", text)).strip()


def _parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


@dataclass(slots=True)
class FeedStatus:
    name: str
    url: str
    status: ApiStatus
    detail: str = ""
    item_count: int = 0


class RSSCollector:
    """Menarik berita dari feed RSS/Atom."""

    def __init__(self, client: NewsAPIClient | None = None) -> None:
        self.client = client or NewsAPIClient(timeout=20.0, max_retries=1)

    # ---------------- parsing ----------------

    @staticmethod
    def _parse(xml_text: str) -> list[dict]:
        """Parse RSS 2.0 atau Atom menjadi list dict mentah."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise ApiError(ApiStatus.ERROR, f"XML tidak valid: {exc}") from exc

        out: list[dict] = []

        # RSS 2.0
        for item in root.iter("item"):
            out.append(
                {
                    "title": _clean(item.findtext("title")),
                    "link": (item.findtext("link") or "").strip(),
                    "description": _clean(
                        item.findtext("description")
                        or item.findtext("content:encoded", namespaces=_NS)
                    ),
                    "pubdate": item.findtext("pubDate")
                    or item.findtext("dc:date", namespaces=_NS),
                }
            )

        # Atom
        for entry in root.iter(f"{{{_NS['atom']}}}entry"):
            link_el = entry.find("atom:link", _NS)
            href = link_el.get("href") if link_el is not None else ""
            out.append(
                {
                    "title": _clean(entry.findtext("atom:title", namespaces=_NS)),
                    "link": (href or "").strip(),
                    "description": _clean(
                        entry.findtext("atom:summary", namespaces=_NS)
                        or entry.findtext("atom:content", namespaces=_NS)
                    ),
                    "pubdate": entry.findtext("atom:updated", namespaces=_NS)
                    or entry.findtext("atom:published", namespaces=_NS),
                }
            )

        return out

    # ---------------- kesehatan ----------------

    def probe(self, feed: dict[str, str]) -> FeedStatus:
        """Uji satu feed tanpa melempar."""
        try:
            body, _ = self.client.get_text(feed["url"])
        except ApiError as exc:
            return FeedStatus(feed["name"], feed["url"], exc.status, exc.detail)
        except Exception as exc:  # noqa: BLE001 - laporan, bukan crash
            return FeedStatus(feed["name"], feed["url"], ApiStatus.ERROR, str(exc)[:120])
        try:
            rows = self._parse(body)
        except ApiError as exc:
            return FeedStatus(feed["name"], feed["url"], exc.status, exc.detail)
        if not rows:
            return FeedStatus(feed["name"], feed["url"], ApiStatus.EMPTY, "feed kosong")
        return FeedStatus(
            feed["name"],
            feed["url"],
            ApiStatus.OK,
            "feed hidup",
            item_count=len(rows),
        )

    def health(self, target: str | None = None) -> list[FeedStatus]:
        """Kesehatan semua feed (atau hanya milik satu target)."""
        targets = [target] if target else list(FEEDS)
        out: list[FeedStatus] = []
        seen: set[str] = set()
        for tgt in targets:
            for feed in FEEDS.get(tgt, []):
                if feed["url"] in seen:
                    continue
                seen.add(feed["url"])
                out.append(self.probe(feed))
        return out

    def health_reports(self, target: str | None = None) -> list[HealthReport]:
        """Versi `HealthReport` agar seragam dengan adapter API."""
        return [
            HealthReport(
                provider=f"rss:{s.name}",
                status=s.status,
                detail=s.detail,
                sample_size=s.item_count,
            )
            for s in self.health(target)
        ]

    # ---------------- penarikan ----------------

    def fetch(self, target: str, limit: int = 50) -> list[NewsItem]:
        """Tarik berita relevan untuk satu target dari semua feed-nya."""
        if target not in TARGET_KEYWORDS:
            raise ValueError(f"target di luar universe terkunci: {target}")

        scored: list[tuple[int, NewsItem]] = []
        seen_urls: set[str] = set()

        for feed in FEEDS.get(target, []):
            try:
                body, _ = self.client.get_text(feed["url"])
                rows = self._parse(body)
            except (ApiError, Exception):  # noqa: BLE001 - satu feed mati tidak fatal
                continue

            for row in rows:
                title = (row.get("title") or "").strip()
                link = (row.get("link") or "").strip()
                if not title:
                    continue
                key = link or title
                if key in seen_urls:
                    continue
                haystack = f"{title} {row.get('description') or ''}"
                if not matches_target(haystack, target):
                    continue
                seen_urls.add(key)
                scored.append(
                    (
                        score_relevance(haystack, target),
                        NewsItem(
                            source=f"rss:{feed['name']}",
                            title=title,
                            url=link or None,
                            body=(row.get("description") or "").strip() or None,
                            published_at=_parse_date(row.get("pubdate")),
                            query_target=target,
                            payload={"feed": feed["name"], "url": feed["url"]},
                        ),
                    )
                )

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:limit]]
