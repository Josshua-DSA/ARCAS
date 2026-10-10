"""Normalization, deduplication, language detection, and time-alignment."""

import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from backend.src.schema import Article, Lang, RawArticle


class ArticleCleaner:
    """Prepares raw incoming articles for pipeline consumption."""

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Cleans whitespace, HTML tags, and non-printable characters."""
        if not text:
            return ""
        # Remove HTML tags
        clean = re.sub(r"<[^>]+>", " ", text)
        # Normalize whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    @staticmethod
    def compute_article_id(title: str, body: Optional[str]) -> str:
        """Generates sha256(norm(title)+norm(body))[:16] per SCHEMA."""
        norm_title = ArticleCleaner.normalize_text(title).lower()
        norm_body = ArticleCleaner.normalize_text(body).lower() if body else ""
        content = (norm_title + norm_body).encode("utf-8")
        return hashlib.sha256(content).hexdigest()[:16]

    @staticmethod
    def detect_language(title: str, body: Optional[str]) -> Lang:
        """Simple heuristic language detector for ID vs EN."""
        combined = (title + " " + (body or "")).lower()
        id_markers = [" yang ", " di ", " dan ", " dari ", " ini ", " untuk ", " pada ", " dengan ", " saham ", " rupiah "]
        en_markers = [" the ", " in ", " and ", " of ", " to ", " for ", " on ", " with ", " market ", " stock "]

        id_score = sum(1 for m in id_markers if m in combined)
        en_score = sum(1 for m in en_markers if m in combined)

        if id_score > en_score and id_score > 0:
            return Lang.ID
        elif en_score > id_score and en_score > 0:
            return Lang.EN
        elif id_score > 0:
            return Lang.ID
        return Lang.OTHER

    @staticmethod
    def compute_effective_trading_date(
        published_at: Optional[datetime],
        target_asset: str,
        session_close_hour_utc: int = 21,
    ) -> date:
        """
        Aligns published datetime to the correct trading date.
        Rule: News published after daily market session close (or weekend)
        maps to the next trading day to prevent lookahead bias.
        """
        if published_at is None:
            return datetime.now(timezone.utc).date()

        # Ensure UTC timezone
        if published_at.tzinfo is None:
            dt = published_at.replace(tzinfo=timezone.utc)
        else:
            dt = published_at.astimezone(timezone.utc)

        # 24-hr assets cut-off 00:00 UTC; others cut-off at session close
        is_24h = target_asset in {"XAU", "OIL", "CU", "NG", "BTC", "USDIDR", "DXY"}
        cutoff_hour = 0 if is_24h else session_close_hour_utc

        eff_date = dt.date()
        if dt.hour >= cutoff_hour and not is_24h:
            eff_date = eff_date + timedelta(days=1)

        # Skip weekend to Monday if traditional exchange
        if target_asset not in {"BTC"}:
            if eff_date.weekday() == 5:  # Saturday -> Monday
                eff_date += timedelta(days=2)
            elif eff_date.weekday() == 6:  # Sunday -> Monday
                eff_date += timedelta(days=1)

        return eff_date

    @classmethod
    def process_raw(cls, raw: RawArticle) -> Article:
        """Transforms a RawArticle into a normalized Article contract."""
        clean_title = cls.normalize_text(raw.title)
        clean_body = cls.normalize_text(raw.body) if raw.body else None
        art_id = cls.compute_article_id(clean_title, clean_body)
        lang = cls.detect_language(clean_title, clean_body)

        # Basic effective dates
        effective_dates: dict[str, date] = {}
        if raw.query_target:
            effective_dates[raw.query_target] = cls.compute_effective_trading_date(
                raw.published_at, raw.query_target
            )

        return Article(
            article_id=art_id,
            source=raw.source,
            url=raw.url,
            title=clean_title,
            body=clean_body,
            language=lang,
            published_at=raw.published_at,
            fetched_at=raw.fetched_at,
            effective_trading_date=effective_dates,
            duplicate_of=None,
            market_relevant=True,
        )
