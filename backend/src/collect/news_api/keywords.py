"""Kata kunci relevansi target — dipakai adapter untuk memfilter berita.

Bersumber dari `data/source_registry.yaml` (`targets.<ID>.keywords`) dan
`macro.keywords`, diperluas untuk mencakup istilah pasar yang lazim.

Pencocokan memakai word-boundary regex, bukan substring. Tanpa ini kata kunci
pendek seperti "war" akan cocok di "software", "award", "toward", "hardware"
dan meloloskan berita yang sama sekali tidak relevan.
"""

from __future__ import annotations

import re
from functools import lru_cache

TARGET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "XAU": (
        "gold", "bullion", "safe haven", "safe-haven", "real yield",
        "real yields", "emas", "xau", "precious metal", "precious metals",
        "gold price", "gold prices", "gold futures", "comex", "spot gold",
    ),
    "RATE_UST": (
        "treasury", "treasuries", "treasury yield", "treasury yields",
        "bond yield", "bond yields", "yield curve", "10-year", "ten-year",
        "two-year", "2-year", "fed funds", "fomc", "federal reserve",
        "rate cut", "rate cuts", "rate hike", "rate hikes", "powell",
        "monetary policy", "obligasi", "yield",
    ),
    "SPX": (
        "s&p", "s&p 500", "sp500", "spx", "wall street", "equities",
        "stock market", "stock markets", "stocks", "earnings", "nasdaq",
        "dow jones", "risk appetite", "equity market", "index futures",
        "blue chip", "blue chips",
    ),
}

# Kata kunci makro: menambah skor, tetapi TIDAK cukup sendirian untuk
# meloloskan berita — butuh minimal satu kata kunci target-spesifik.
MACRO_KEYWORDS: tuple[str, ...] = (
    "fed", "fomc", "inflation", "cpi", "pce", "jobs report", "payrolls",
    "tariff", "tariffs", "rate cut", "rate hike", "war", "recession", "gdp",
)


@lru_cache(maxsize=256)
def _pattern(keyword: str) -> re.Pattern[str]:
    """Kompilasi kata kunci menjadi regex word-boundary, case-insensitive.

    Spasi di dalam frasa dilonggarkan agar "safe haven" juga cocok dengan
    "safe-haven" dan "safe  haven".
    """
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", keyword.strip()) if p]
    body = r"[\s\-]*".join(parts)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def count_hits(text: str, keywords: tuple[str, ...]) -> int:
    """Jumlah kata kunci berbeda yang cocok di teks."""
    return sum(1 for kw in keywords if _pattern(kw).search(text))


def score_relevance(text: str, target: str) -> int:
    """Skor relevansi: 2x kata kunci target + 1x kata kunci makro.

    Skor 0 berarti tidak relevan sama sekali.
    """
    if not text:
        return 0
    specific = count_hits(text, TARGET_KEYWORDS.get(target, ()))
    macro = count_hits(text, MACRO_KEYWORDS)
    return specific * 2 + macro


def matches_target(text: str, target: str, require_specific: bool = True) -> bool:
    """True bila teks relevan untuk target.

    `require_specific=True` (default) menolak berita yang hanya cocok dengan
    kata kunci makro seperti "inflation" tanpa menyebut targetnya.
    """
    if not text:
        return False
    specific = count_hits(text, TARGET_KEYWORDS.get(target, ()))
    if require_specific and specific == 0:
        return False
    return (specific > 0) or (count_hits(text, MACRO_KEYWORDS) > 0)
