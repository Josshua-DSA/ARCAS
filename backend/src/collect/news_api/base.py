"""Primitif bersama untuk seluruh adapter news API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable

from backend.src.schema import RawArticle

# Target universe terkunci (RULES: murni 3).
LOCKED_TARGETS: tuple[str, ...] = ("XAU", "RATE_UST", "SPX")


def utcnow() -> datetime:
    """Timestamp UTC timezone-aware — dipakai sebagai fetched_at."""
    return datetime.now(timezone.utc)


class ApiStatus(str, Enum):
    """Hasil identifikasi satu penyedia API."""

    OK = "ok"                    # kunci valid, ada data
    EMPTY = "empty"              # kunci valid, tapi nol hasil
    NO_KEY = "no_key"            # env var tidak diset
    UNAUTHORIZED = "unauthorized"  # kunci ditolak (401/403)
    RATE_LIMITED = "rate_limited"  # 429
    PREMIUM_ONLY = "premium_only"  # endpoint butuh langganan
    ERROR = "error"              # jaringan / parse gagal


@dataclass(slots=True)
class HealthReport:
    """Ringkasan kesehatan satu penyedia API."""

    provider: str
    status: ApiStatus
    detail: str = ""
    latency_ms: float | None = None
    sample_size: int = 0
    sample_title: str | None = None

    @property
    def usable(self) -> bool:
        return self.status in (ApiStatus.OK, ApiStatus.EMPTY)

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status.value,
            "usable": self.usable,
            "detail": self.detail,
            "latency_ms": self.latency_ms,
            "sample_size": self.sample_size,
            "sample_title": self.sample_title,
        }


@dataclass(slots=True)
class NewsItem:
    """Satu berita mentah, belum dinormalisasi (belum punya article_id)."""

    source: str
    title: str
    url: str | None = None
    body: str | None = None
    published_at: datetime | None = None
    query_target: str | None = None
    vendor_sentiment: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)

    def to_raw_article(self, fetched_at: datetime | None = None) -> RawArticle:
        """Konversi ke kontrak `RawArticle` (SCHEMA)."""
        return RawArticle(
            source=self.source,
            url=self.url,
            title=self.title,
            body=self.body,
            published_at=self.published_at,
            fetched_at=fetched_at or utcnow(),
            query_target=self.query_target,
            vendor_sentiment=self.vendor_sentiment,
        )


@runtime_checkable
class NewsAPIAdapter(Protocol):
    """Kontrak setiap adapter penyedia berita."""

    name: str
    env_key: str | None

    def is_configured(self) -> bool:
        """True bila kredensial tersedia."""
        ...

    def probe(self) -> HealthReport:
        """Uji ringan: kunci valid? ada data?"""
        ...

    def fetch(self, target: str, limit: int = 50) -> list[NewsItem]:
        """Tarik berita untuk satu target universe."""
        ...
