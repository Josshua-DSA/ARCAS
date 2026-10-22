"""HTTP client tipis dengan retry/backoff dan klasifikasi error.

RULES: retry + backoff untuk HTTP/API; kegagalan sumber tidak menghentikan
pipeline (dicatat sebagai status, bukan exception yang naik).
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from backend.src.collect.news_api.base import ApiStatus

DEFAULT_UA = "FInews/0.6 (+research; contact: local)"


class ApiError(Exception):
    """Kegagalan HTTP yang sudah diklasifikasi."""

    def __init__(self, status: ApiStatus, detail: str, http_code: int | None = None):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.http_code = http_code


class NewsAPIClient:
    """Klien GET JSON dengan retry eksponensial.

    Tidak menyimpan kredensial di log. Nilai `params` yang mengandung token
    disamarkan saat error dilaporkan.
    """

    def __init__(
        self,
        timeout: float = 20.0,
        max_retries: int = 2,
        backoff_base: float = 1.5,
        user_agent: str = DEFAULT_UA,
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.user_agent = user_agent

    # ---------------- internals ----------------

    @staticmethod
    def _mask(params: dict[str, Any]) -> dict[str, Any]:
        secretish = ("token", "apikey", "api_key", "api_token", "key")
        return {
            k: ("***" if any(s in k.lower() for s in secretish) else v)
            for k, v in params.items()
        }

    def _classify(self, exc: urllib.error.HTTPError, body: str) -> ApiError:
        code = exc.code
        low = body.lower()
        if code in (401, 403):
            return ApiError(ApiStatus.UNAUTHORIZED, f"HTTP {code}: kredensial ditolak", code)
        if code == 429:
            return ApiError(ApiStatus.RATE_LIMITED, "HTTP 429: rate limit", code)
        if code == 404:
            return ApiError(ApiStatus.ERROR, "HTTP 404: endpoint tidak ada", code)
        # Alpha Vantage & sejenisnya mengembalikan 200/4xx dengan pesan premium
        if "premium" in low or "subscribe" in low:
            return ApiError(ApiStatus.PREMIUM_ONLY, "endpoint butuh langganan premium", code)
        if code >= 500:
            return ApiError(
                ApiStatus.ERROR,
                f"HTTP {code}: penyedia bermasalah (sering berarti kuota harian habis)",
                code,
            )
        return ApiError(ApiStatus.ERROR, f"HTTP {code}: {body[:160]}", code)

    def _once(
        self, url: str, params: dict[str, Any], headers: dict[str, str] | None = None
    ) -> tuple[Any, float]:
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        hdrs = {"User-Agent": self.user_agent}
        if headers:
            hdrs.update(headers)
        req = urllib.request.Request(url, headers=hdrs)
        started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            latency = (time.perf_counter() - started) * 1000.0
        try:
            return json.loads(raw), latency
        except json.JSONDecodeError as exc:
            raise ApiError(ApiStatus.ERROR, f"respons bukan JSON: {raw[:120]}") from exc

    # ---------------- public ----------------

    def get_json(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[Any, float]:
        """GET JSON dengan retry. Melempar `ApiError` setelah percobaan habis.

        `headers` tambahan dipakai vendor yang memakai Bearer token
        (mis. Eulerpool) alih-alih kunci di query string.
        """
        params = dict(params or {})
        last: ApiError | None = None

        for attempt in range(self.max_retries + 1):
            try:
                return self._once(url, params, headers)
            except urllib.error.HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8", errors="replace")
                except Exception:  # pragma: no cover - best effort
                    pass
                err = self._classify(exc, body)
                # 401/403/404/premium tidak akan sembuh dengan retry
                if err.status in (ApiStatus.UNAUTHORIZED, ApiStatus.PREMIUM_ONLY) or exc.code == 404:
                    raise err from exc
                last = err
            except urllib.error.URLError as exc:
                last = ApiError(ApiStatus.ERROR, f"jaringan: {exc.reason}")
            except TimeoutError:
                last = ApiError(ApiStatus.ERROR, "timeout")
            except ApiError as exc:
                last = exc

            if attempt < self.max_retries:
                time.sleep(self.backoff_base ** attempt)

        raise last or ApiError(ApiStatus.ERROR, "gagal tanpa detail")

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> tuple[str, float]:
        """GET teks mentah (untuk RSS/XML)."""
        params = dict(params or {})
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        started = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        return body, (time.perf_counter() - started) * 1000.0


def env(name: str) -> str:
    """Baca env var, strip spasi, kembalikan string kosong bila tidak ada."""
    return (os.getenv(name) or "").strip()
