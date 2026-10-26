"""Registry penyedia API berita — identifikasi kredensial & kesehatan.

Ini titik masuk "identify API": memindai env, melaporkan penyedia mana yang
siap dipakai, tanpa pernah mencetak nilai kredensial.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from backend.src.collect.news_api.alphavantage import AlphaVantageAdapter
from backend.src.collect.news_api.base import HealthReport, NewsAPIAdapter
from backend.src.collect.news_api.eulerpool import EulerpoolAdapter
from backend.src.collect.news_api.finnhub import FinnhubAdapter
from backend.src.collect.news_api.marketaux import MarketauxAdapter

logger = logging.getLogger(__name__)

DEFAULT_ENV_FILE = Path(".env")


@dataclass(slots=True)
class ApiSpec:
    """Metadata satu penyedia API."""

    name: str
    env_key: str | None
    adapter: type
    free_tier: str
    note: str = ""


def _specs() -> list[ApiSpec]:
    return [
        ApiSpec(
            name="finnhub",
            env_key="FINNHUB_API_KEY",
            adapter=FinnhubAdapter,
            free_tier="60 req/menit",
            note="Berita umum/forex/merger. Tanpa pencarian kata kunci.",
        ),
        ApiSpec(
            name="marketaux",
            env_key="MARKETAUX_API_KEY",
            adapter=MarketauxAdapter,
            free_tier="100 req/hari",
            note="Filter simbol XAUUSD/GC=F kosong di paket gratis; pakai countries=us.",
        ),
        ApiSpec(
            name="eulerpool",
            env_key="EULERPOOL_API_KEY",
            adapter=EulerpoolAdapter,
            free_tier="kuota harian kecil — patuhi 10-100 req/hari",
            note=(
                "Berita pasar via API resmi (Bearer token). Satu request "
                "melayani semua target: pakai fetch_all(), bukan fetch() per target. "
                "Filter target dilakukan lokal (field 'related' selalu kosong)."
            ),
        ),
        ApiSpec(
            name="alphavantage",
            env_key="ALPHAVANTAGE_API_KEY",
            adapter=AlphaVantageAdapter,
            free_tier="25 req/hari (NEWS_SENTIMENT premium)",
            note="NEWS_SENTIMENT butuh langganan pada kunci gratis.",
        ),
    ]


class ApiRegistry:
    """Kumpulan adapter yang bisa diidentifikasi dan dipanggil."""

    def __init__(self, load_env: bool = True, env_file: Path | str = DEFAULT_ENV_FILE) -> None:
        if load_env:
            self._load_env(Path(env_file))
        self._specs = _specs()
        self._adapters: dict[str, NewsAPIAdapter] = {
            spec.name: spec.adapter() for spec in self._specs
        }

    @staticmethod
    def _load_env(path: Path) -> None:
        """Muat .env bila ada. Tidak melempar bila file tidak ditemukan."""
        if not path.exists():
            return
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=str(path), override=False)
        except ImportError:  # pragma: no cover - dotenv opsional
            logger.debug("python-dotenv tidak terpasang; kunci API hanya dari env proses")

    # ---------------- identifikasi ----------------

    def specs(self) -> list[ApiSpec]:
        return list(self._specs)

    def configured(self) -> list[str]:
        """Nama penyedia yang punya kredensial di env."""
        return [name for name, a in self._adapters.items() if a.is_configured()]

    def missing(self) -> list[str]:
        """Nama penyedia yang env var-nya kosong."""
        return [name for name, a in self._adapters.items() if not a.is_configured()]

    def get(self, name: str) -> NewsAPIAdapter:
        if name not in self._adapters:
            raise KeyError(f"penyedia tidak dikenal: {name}")
        return self._adapters[name]

    def health(self, probe: bool = True) -> list[HealthReport]:
        """Laporan kesehatan semua penyedia.

        `probe=False` hanya memeriksa keberadaan kredensial (tanpa jaringan).
        """
        reports: list[HealthReport] = []
        for spec in self._specs:
            adapter = self._adapters[spec.name]
            if not adapter.is_configured():
                from backend.src.collect.news_api.base import ApiStatus

                reports.append(
                    HealthReport(
                        provider=spec.name,
                        status=ApiStatus.NO_KEY,
                        detail=f"{spec.env_key} tidak diset",
                    )
                )
            elif probe:
                reports.append(adapter.probe())
            else:
                from backend.src.collect.news_api.base import ApiStatus

                reports.append(
                    HealthReport(
                        provider=spec.name,
                        status=ApiStatus.OK,
                        detail="kredensial tersedia (belum diuji)",
                    )
                )
        return reports

    def usable(self) -> list[str]:
        """Penyedia yang benar-benar bisa dipakai (probe sukses)."""
        return [r.provider for r in self.health(probe=True) if r.usable]


def identify_apis(probe: bool = True) -> list[dict]:
    """Fungsi kenyamanan: kembalikan laporan sebagai list of dict."""
    return [r.as_dict() for r in ApiRegistry().health(probe=probe)]
