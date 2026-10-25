"""Normalization, deduplication, language detection, and time-alignment."""

import hashlib
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

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

    #: Detektor lingua dibangun sekali saja: memuat model bahasa butuh
    #: ~100 ms, sedangkan deteksi per artikel hanya ~0,1 ms. Membangunnya
    #: per panggilan akan memperlambat ingest tanpa alasan.
    #: Tri-state: None = belum dicoba, False = pustaka tidak ada,
    #: selain itu objek detektor siap pakai.
    _lingua_detector: object = None

    @classmethod
    def _get_lingua_detector(cls) -> Any:
        """Bangun (sekali) detektor lingua EN vs ID, atau None bila absen."""
        if cls._lingua_detector is not None:
            return cls._lingua_detector or None
        try:
            from lingua import Language, LanguageDetectorBuilder

            cls._lingua_detector = LanguageDetectorBuilder.from_languages(
                Language.ENGLISH, Language.INDONESIAN
            ).with_preloaded_language_models().build()
        except ImportError:
            # Penanda False (bukan None) agar kegagalan tidak dicoba ulang
            # pada setiap artikel.
            cls._lingua_detector = False
        return cls._lingua_detector or None

    @staticmethod
    def detect_language(title: str, body: Optional[str]) -> Lang:
        """Deteksi bahasa ID/EN dengan lingua; heuristik hanya sebagai cadangan.

        Heuristik kata fungsi lama salah menandai headline emas pendek
        sebagai `other` (mis. "Gold rallies as Fed signals rate cuts ahead"
        tidak memuat satu pun penanda Inggris), dan karena pipeline kini
        melewati artikel non-Inggris, kesalahan itu akan membuang berita
        yang justru jadi sasaran model. `lingua` menangani teks pendek
        dengan benar; heuristik dipertahankan hanya untuk lingkungan yang
        tidak memasang paketnya.
        """
        combined = (title + " " + (body or "")).strip()
        if not combined:
            return Lang.OTHER

        detector = ArticleCleaner._get_lingua_detector()
        if detector is not None:
            from lingua import Language

            hasil = detector.detect_language_of(combined)
            # Perbandingan wajib pakai `==`, bukan `is`: anggota enum lingua
            # dibuat ulang per pemanggilan modul internal, sehingga `is`
            # gagal walau bahasanya benar (terbukti: confidence 0.996 ENGLISH
            # tetapi `hasil is Language.ENGLISH` bernilai False).
            if hasil == Language.ENGLISH:
                return Lang.EN
            if hasil == Language.INDONESIAN:
                return Lang.ID
            return Lang.OTHER

        return ArticleCleaner._detect_language_heuristic(combined)

    @staticmethod
    def _detect_language_heuristic(combined: str) -> Lang:
        """Cadangan tanpa dependensi: hitung penanda kata fungsi ID vs EN."""
        text = combined.lower()
        id_markers = [" yang ", " di ", " dan ", " dari ", " ini ", " untuk ", " pada ", " dengan ", " saham ", " rupiah "]
        en_markers = [" the ", " in ", " and ", " of ", " to ", " for ", " on ", " with ", " market ", " stock "]

        id_score = sum(1 for m in id_markers if m in text)
        en_score = sum(1 for m in en_markers if m in text)

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

        # Core3 convention: XAU cut-off 00:00 UTC; RATE_UST/SPX cut-off
        # at session close. All three halt on weekends.
        is_24h = target_asset == "XAU"
        cutoff_hour = 0 if is_24h else session_close_hour_utc

        eff_date = dt.date()
        if dt.hour >= cutoff_hour and not is_24h:
            eff_date = eff_date + timedelta(days=1)

        # Skip weekend to Monday (CME/CBOE/SNP calendars)
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
