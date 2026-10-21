"""Adapter Eulerpool — berita pasar umum lewat API resmi.

Endpoint: GET https://api.eulerpool.com/api/1/equity-extended/market-news?limit=N
Auth:     Authorization: Bearer <EULERPOOL_API_KEY>

Kenapa satu request untuk semua target: endpoint market-news mengembalikan
satu daftar berita pasar (hingga 200 item) per panggilan. Memanggilnya tiga
kali (satu per target) hanya membuang kuota 10–100/hari. Jadi `fetch()` untuk
target apa pun mengambil daftar yang sama, lalu memfilter dengan kata kunci
target secara lokal — biaya kuota tetap 1.

Batas yang diketahui dari dokumentasi OpenAPI resmi:
  - `limit` default 50, maksimum 200 (bukan 200+).
  - Tidak ada parameter tanggal, simbol, atau kata kunci pada endpoint ini.
    Karena itu filter target dilakukan lokal memakai `keywords.py`.

Catatan penting yang ditemukan saat verifikasi:
  - Field `related` SELALU kosong pada sampel 200 item. Jadi tidak ada
    pemetaan aset terstruktur dari vendor; kita tidak boleh mengarangnya.
  - Sebagian besar URL mengarah ke `news.google.com/rss/articles/...`,
    sebagian ke domain asli (cnbc.com, bloomberg.com). Sumber asli tetap
    disimpan di `source` agar bisa ditelusuri.
  - Konten ini adalah agregasi pihak ketiga, sehingga tumpang tindih dengan
    Finnhub wajar. `save_raw_articles` men-dedup per (source, url) — jadi
    berita yang sama dari dua vendor akan tersimpan dua kali dengan source
    berbeda. Itu disengaja: kita ingin tahu siapa melaporkan apa.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

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
from backend.src.collect.news_api.quota import DailyQuota, QuotaExceeded

try:  # .env opsional; tanpa dotenv kunci bisa tetap datang dari lingkungan proses
    from pathlib import Path as _Path

    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(dotenv_path=str(_Path(".env")), override=False)
except ImportError:  # pragma: no cover
    pass

BASE = "https://api.eulerpool.com/api/1/equity-extended/market-news"

# Batas keras dari dokumentasi: default 50, max 200.
MAX_ITEMS_PER_REQUEST = 200
DEFAULT_ITEMS = 100

# Umur maksimum berita yang diterima (hari). Berita pasar yang lebih tua dari
# ini tidak berguna untuk sentimen harian, dan hanya menambah baris.
MAX_AGE_DAYS = 7


@runtime_checkable
class _JsonClient(Protocol):
    """Kontrak minimal klien HTTP — memudahkan penggantian di test."""

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[Any, float]: ...


class EulerpoolAdapter:
    """Adapter berita pasar Eulerpool (satu request per tarikan)."""

    name = "eulerpool"
    env_key = "EULERPOOL_API_KEY"

    def __init__(
        self,
        client: _JsonClient | None = None,
        key: str | None = None,
        quota: DailyQuota | None = None,
    ) -> None:
        self.client = client or NewsAPIClient()
        self._key = key if key is not None else env(self.env_key)
        self.quota = quota

    def is_configured(self) -> bool:
        return bool(self._key)

    # ---------------- internals ----------------

    def _raw_market_news(self, limit: int = DEFAULT_ITEMS) -> tuple[list[dict[str, Any]], float]:
        """Satu panggilan HTTP. Memesan kuota lebih dulu bila dijaga.

        `limit` di-clamp ke 200 — meminta lebih hanya akan ditolak/dipotong
        server dan tetap dihitung satu request.
        """
        limit = max(1, min(int(limit), MAX_ITEMS_PER_REQUEST))

        if self.quota is not None:
            self.quota.reserve(1)  # melempar QuotaExceeded bila habis

        try:
            data, latency = self.client.get_json(
                BASE,
                {"limit": limit},
                headers={"Authorization": f"Bearer {self._key}"},
            )
        except QuotaExceeded:
            raise
        except ApiError:
            # Request tidak sampai / ditolak sebelum diproses: kembalikan slot.
            if self.quota is not None:
                self.quota.refund(1)
            raise
        except Exception:
            if self.quota is not None:
                self.quota.refund(1)
            raise

        if isinstance(data, dict):
            msg = str(data.get("error") or data)[:200]
            raise ApiError(ApiStatus.ERROR, f"eulerpool: {msg}")
        if not isinstance(data, list):
            raise ApiError(ApiStatus.ERROR, f"eulerpool: respons tak terduga {type(data).__name__}")
        return data, latency

    @staticmethod
    def _parse_published(row: dict[str, Any]) -> datetime | None:
        """`datetime` dari Eulerpool berupa epoch detik (int)."""
        ts = row.get("datetime")
        if ts is None:
            return None
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _is_fresh(published: datetime | None, now: datetime | None = None) -> bool:
        """Tolak berita lebih tua dari MAX_AGE_DAYS atau bertanggal masa depan."""
        if published is None:
            return True
        ref = now or datetime.now(timezone.utc)
        umur = (ref - published).total_seconds() / 86400
        return -1.0 <= umur <= MAX_AGE_DAYS

    def _to_item(self, row: dict[str, Any], target: str) -> NewsItem:
        vendor_source = (row.get("source") or "unknown").strip()
        return NewsItem(
            # Prefix vendor supaya bisa dibedakan dari finnhub/reuters dsb.
            source=f"eulerpool:{vendor_source}",
            title=(row.get("headline") or "").strip(),
            url=row.get("url"),
            # `summary` dipakai sebagai body; seringkali hanya mengulang judul,
            # itu tidak masalah — normalizer yang memutuskan.
            body=(row.get("summary") or "").strip() or None,
            published_at=self._parse_published(row),
            query_target=target,
            # Eulerpool tidak memberi skor sentimen pada endpoint ini.
            vendor_sentiment=None,
            payload={
                "eulerpool_category": row.get("category"),
                "eulerpool_image": row.get("image"),
                "eulerpool_related": row.get("related"),
                "eulerpool_source": vendor_source,
            },
        )

    # ---------------- public ----------------

    def probe(self) -> HealthReport:
        """Cek kunci dengan satu request minimum (limit=1)."""
        if not self.is_configured():
            return HealthReport(
                provider=self.name,
                status=ApiStatus.NO_KEY,
                detail=f"{self.env_key} tidak diset",
            )
        try:
            data, latency = self._raw_market_news(limit=1)
        except QuotaExceeded as exc:
            return HealthReport(
                provider=self.name, status=ApiStatus.ERROR, detail=str(exc)[:200]
            )
        except ApiError as exc:
            return HealthReport(provider=self.name, status=exc.status, detail=exc.detail)
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

        Biaya kuota: **1 request**, berapa pun jumlah target yang memanggilnya
        pada hari yang sama? Tidak — tetap 1 per pemanggilan `fetch()`. Karena
        itu CLI sebaiknya menarik daftar sekali lewat `fetch_all()`.
        """
        if not self.is_configured():
            raise ApiError(ApiStatus.NO_KEY, f"{self.env_key} tidak diset")
        if target not in TARGET_KEYWORDS:
            raise ValueError(f"target di luar universe terkunci: {target}")

        # Ambil lebih banyak daripada `limit` karena filter lokal akan membuang
        # sebagian besar item (hanya ~10% relevan untuk target tertentu).
        rows, _ = self._raw_market_news(limit=MAX_ITEMS_PER_REQUEST)

        scored: list[tuple[int, NewsItem]] = []
        seen: set[str] = set()
        for row in rows:
            title = (row.get("headline") or "").strip()
            if not title:
                continue
            published = self._parse_published(row)
            if not self._is_fresh(published):
                continue
            haystack = f"{title} {row.get('summary') or ''}"
            if not matches_target(haystack, target):
                continue
            url = row.get("url") or ""
            key = url or title.lower()
            if key in seen:
                continue
            seen.add(key)
            scored.append((score_relevance(haystack, target), self._to_item(row, target)))

        scored.sort(key=lambda pair: (pair[0], pair[1].published_at or datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return [item for _, item in scored[:limit]]

    def fetch_all(self, limit_per_target: int = 50) -> dict[str, list[NewsItem]]:
        """Tarik SEKALI, lalu bagi ke tiga target.

        Ini jalur yang dipakai CLI: satu request memberi berita untuk XAU,
        RATE_UST, dan SPX sekaligus. Hemat kuota 3x dibanding memanggil
        `fetch()` per target.
        """
        if not self.is_configured():
            raise ApiError(ApiStatus.NO_KEY, f"{self.env_key} tidak diset")

        rows, _ = self._raw_market_news(limit=MAX_ITEMS_PER_REQUEST)

        hasil: dict[str, list[NewsItem]] = {t: [] for t in TARGET_KEYWORDS}
        skor: dict[str, list[tuple[int, NewsItem]]] = {t: [] for t in TARGET_KEYWORDS}
        seen: dict[str, set[str]] = {t: set() for t in TARGET_KEYWORDS}

        for row in rows:
            title = (row.get("headline") or "").strip()
            if not title:
                continue
            published = self._parse_published(row)
            if not self._is_fresh(published):
                continue
            haystack = f"{title} {row.get('summary') or ''}"
            url = row.get("url") or ""
            key = url or title.lower()

            for target in TARGET_KEYWORDS:
                if not matches_target(haystack, target):
                    continue
                if key in seen[target]:
                    continue
                seen[target].add(key)
                skor[target].append((score_relevance(haystack, target), self._to_item(row, target)))

        for target in TARGET_KEYWORDS:
            skor[target].sort(
                key=lambda pair: (
                    pair[0],
                    pair[1].published_at or datetime.min.replace(tzinfo=timezone.utc),
                ),
                reverse=True,
            )
            hasil[target] = [item for _, item in skor[target][:limit_per_target]]
        return hasil
