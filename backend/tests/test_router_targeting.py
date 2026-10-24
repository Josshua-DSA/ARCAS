"""FR-3: penandaan target harus presisi dan dua bahasa.

Tiga bug yang dikunci di sini, semuanya ditemukan lewat pengujian langsung
terhadap `TargetRouter` pada 2026-10-24 (bukan lewat type checker):

1. **False positive sebutan eksplisit.** `find_explicit_mentions` memakai
   `str.find`, sehingga "gold" cocok di dalam "**Goldman** Sachs". Berita
   yang tidak menyebut emas sama sekali tetap ditandai XAU dengan
   `Basis.EXPLICIT` — keyakinan tertinggi — dan mencemari sentimen XAU.
   Bug ini tidak terlihat dari test mana pun karena sebelumnya tidak ada
   test yang menyentuh `find_explicit_mentions` maupun `detect_themes`.

2. **Kamus tema satu bahasa.** `detect_themes` hanya memuat frasa Indonesia
   untuk sebagian tema ("geopolitik", "panic selling") dan frasa Inggris
   untuk yang lain, sehingga korpus campuran — RSS Inggris + media Indonesia —
   kehilangan separuh sinyal makro. Terukur: 9 dari 12 kalimat uji gagal.

3. **Substring pada tema.** `any(kw in lower ...)` membuat "rates" cocok di
   dalam kata lain dan tidak menghormati batas kata.

Dampaknya berantai: tema adalah satu-satunya jalur bagi artikel yang tidak
menyebut aset secara langsung (`route_article` → `impact_graph.yaml`). Tema
yang gagal terdeteksi = impact tidak pernah terbentuk, dan karena
`LOCKED_UNIVERSE` hanya berisi XAU/RATE_UST/SPX, tidak ada jaring pengaman.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.src.tagging.router import TargetRouter

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def router() -> TargetRouter:
    return TargetRouter(
        aliases_path=ROOT / "data/universe/aliases.csv",
        impact_graph_path=ROOT / "data/impact_graph.yaml",
    )


class TestExplicitMentionBoundary:
    """Alias tidak boleh cocok sebagai potongan kata lain."""

    @pytest.mark.parametrize(
        "teks",
        [
            "Goldman Sachs raises its target price",
            "Goldmann berkomentar soal pasar",
            "semasa kecil di Jakarta",
            "emasnya belum dibeli",  # "emas" + akhiran -nya
        ],
    )
    def test_tidak_cocok_sebagai_potongan_kata(self, router: TargetRouter, teks: str) -> None:
        """Kata yang *mengandung* alias tidak boleh dihitung sebagai sebutan.

        "Goldman" mengandung "gold", "semasa" mengandung "emas". Inilah bug
        yang membuat berita non-emas ditandai `Basis.EXPLICIT` untuk XAU.
        """
        assert router.find_explicit_mentions(teks) == []

    def test_alias_utuh_tetap_cocok(self, router: TargetRouter) -> None:
        """Perbaikan tidak boleh mematikan pencocokan yang sah."""
        assert router.find_explicit_mentions("Goldman Sachs cuts gold exposure") == [
            ("XAU", "gold", 19, 23)
        ]

    @pytest.mark.parametrize(
        "teks,asset",
        [
            ("Emas Antam naik Rp 5.000 per gram", "XAU"),
            ("Harga gold menguat hari ini", "XAU"),
            ("US 10-year treasury yield climbs", "RATE_UST"),
            ("S&P 500 closes at record high", "SPX"),
        ],
    )
    def test_alias_sah_masih_terdeteksi(self, router: TargetRouter, teks: str, asset: str) -> None:
        assert asset in [m[0] for m in router.find_explicit_mentions(teks)]

    @pytest.mark.parametrize(
        "teks,asset",
        [
            ("The gold standard debate continues", "XAU"),
            ("Sp500 futures climb", "SPX"),
            ("A gold-plated coin", "XAU"),
        ],
    )
    def test_kata_utuh_bukan_potongan(self, router: TargetRouter, teks: str, asset: str) -> None:
        """Kebalikannya: alias utuh harus tetap cocok walau diikuti tanda hubung.

        "gold standard" dan "Sp500" memang menyebut instrumennya, jadi harus
        positif — berbeda dari "Goldman" yang hanya kebetulan berawalan sama.
        """
        assert asset in [m[0] for m in router.find_explicit_mentions(teks)]

    def test_frasa_berhubung(self, router: TargetRouter) -> None:
        """Spasi/tanda hubung di dalam frasa dilonggarkan."""
        for varian in ("safe haven", "safe-haven", "safe  haven"):
            assert router.find_explicit_mentions(f"Investors buy {varian} assets")


class TestThemeDetection:
    """Tema harus terdeteksi pada kalimat ID maupun EN."""

    @pytest.mark.parametrize(
        "teks,tema",
        [
            # rates_down
            ("Fed cuts rates by 25bps", "rates_down"),
            ("The Fed memangkas suku bunga acuan", "rates_down"),
            ("Pemotongan bunga mulai April", "rates_down"),
            ("Powell gives a dovish signal", "rates_down"),
            # rates_up
            ("Fed raises rates by 25bps", "rates_up"),
            ("The Fed hiked interest rates", "rates_up"),
            ("Naikkan suku bunga acuan", "rates_up"),
            ("Hawkish tone from the ECB", "rates_up"),
            # usd_up
            ("Dollar strengthens against the yen", "usd_up"),
            ("Dolar menguat tajam", "usd_up"),
            ("The dollar rallied overnight", "usd_up"),
            ("Rupiah melemah terhadap dolar", "usd_up"),
            # risk_off
            ("Investors flee to safety amid selloff", "risk_off"),
            ("Pasar panic selling pagi ini", "risk_off"),
            ("Risk aversion grips markets", "risk_off"),
            # geopolitical_tension
            ("Geopolitical tensions escalate in the Middle East", "geopolitical_tension"),
            ("Eskalasi geopolitik Timur Tengah", "geopolitical_tension"),
            ("Middle East conflict escalates", "geopolitical_tension"),
        ],
    )
    def test_tema_terdeteksi_dua_bahasa(self, router: TargetRouter, teks: str, tema: str) -> None:
        assert tema in router.detect_themes(teks), (
            f"{teks!r} seharusnya memicu tema {tema!r}, "
            f"hasil: {router.detect_themes(teks)}"
        )

    def test_teks_netral_tanpa_tema(self, router: TargetRouter) -> None:
        """Tidak boleh ada tema palsu pada kalimat yang tidak relevan."""
        assert router.detect_themes("Cuaca cerah di Jakarta hari ini") == []
        assert router.detect_themes("Persib menang 2-0 atas Persija") == []

    def test_setiap_tema_punya_kata_kunci(self, router: TargetRouter) -> None:
        """Setiap tema di kamus non-kosong, dan semua tema punya istilah EN."""
        for tema, kata in router.THEME_KEYWORDS.items():
            assert kata, f"tema {tema} tidak punya kata kunci"
            assert any(k.isascii() for k in kata), f"tema {tema} tidak punya istilah Inggris"

    def test_konsisten_dengan_impact_graph(self, router: TargetRouter) -> None:
        """Tema yang dideteksi router harus ada di impact_graph.yaml.

        Tema yang terdeteksi tetapi tidak ada di graf adalah sinyal mati:
        terdeteksi lalu dibuang tanpa jejak.
        """
        graf = set(router.impact_graph)
        assert set(router.THEME_KEYWORDS) == graf, (
            f"tema router: {sorted(router.THEME_KEYWORDS)} vs graf: {sorted(graf)}"
        )
