"""News API adapters — identifikasi kredensial & tarik berita real-time.

Lingkup terkunci pada 3 target: XAU, RATE_UST, SPX.
"""

from backend.src.collect.news_api.base import (
    ApiStatus,
    HealthReport,
    NewsAPIAdapter,
    NewsItem,
    utcnow,
)
from backend.src.collect.news_api.client import NewsAPIClient
from backend.src.collect.news_api.registry import ApiRegistry, ApiSpec, identify_apis

__all__ = [
    "ApiSpec",
    "ApiRegistry",
    "ApiStatus",
    "HealthReport",
    "NewsAPIAdapter",
    "NewsAPIClient",
    "NewsItem",
    "identify_apis",
    "utcnow",
]
