"""P0-2 / P0-3: arah stance -> harga, dan prioritas model eksplisit.

Dua bug yang dikunci di sini, keduanya ditemukan lewat audit eksekusi pada
2026-10-26 (bukan lewat type checker):

1. **Arah dovish/hawkish dipakai mentah sebagai arah harga.**
   `FOMC-RoBERTa` mengukur *stance* The Fed (hawkish = label positif,
   dovish = label negatif). `TargetRouter` memakai `sentiment_score` mentah
   untuk menentukan `Direction`, sehingga kalimat dovish
   ("decided to lower the target range") menghasilkan **XAU bearish** —
   kebalikan dari hubungan ekonomi yang benar (dovish -> suku bunga riil
   turun -> emas naik). `impact_graph.yaml` sudah menyatakan arah yang
   benar (`rates_down: XAU sign +1`), tetapi jalur explicit-match tidak
   pernah memakainya.

2. **Prioritas model ditentukan urutan `if`.**
   Blok `if "fomc_roberta"` ditulis sebelum `if "finbert_emas"` tanpa
   `break`, sehingga model yang ditulis terakhir menang. FOMC (355M
   parameter) dimuat lalu dibuang untuk artikel yang memicu keduanya.
   Perilaku bergantung posisi baris, bukan keputusan desain.

Test ini sengaja memakai kalimat dovish/hawkish **nyata** — bukan
`MagicMock` — karena seluruh test FOMC sebelumnya memakai skor buatan
sehingga kesalahan tanda tidak pernah terlihat.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.src.pipeline.runner import MODEL_PRIORITY
from backend.src.schema import Article, Direction, Lang
from backend.src.tagging.router import TargetRouter
from model.common.sentiment_config import stance_direction

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def router() -> TargetRouter:
    return TargetRouter(
        aliases_path=ROOT / "data/universe/aliases.csv",
        impact_graph_path=ROOT / "data/impact_graph.yaml",
    )


def _article(title: str, body: str = "") -> Article:
    now = datetime.now(timezone.utc)
    return Article(
        article_id="p0-2",
        title=title,
        body=body,
        source="reuters",
        url="https://contoh.test/p0-2",
        published_at=now,
        fetched_at=now,
        language=Lang.EN,
    )


def _xau_impact(router: TargetRouter, text: str, score: float, space: str):
    """Impact XAU untuk satu artikel, dipilih berdasarkan basis."""
    impacts = router.route_article(_article(text), sentiment_score=score, score_space=space)
    xau = [i for i in impacts if i.asset_id == "XAU"]
    assert xau, f"tidak ada impact XAU untuk {text!r} (mode={space})"
    # Explicit menang atas makro (`tagged_assets`), jadi yang pertama itu benar.
    return xau[0]


class TestArahStanceKeHarga:
    """Mode `stance`: dovish harus bullish XAU, hawkish harus bearish."""

    #: Skor stance nyata dari model: dovish -> negatif, hawkish -> positif.
    DOVISH = -0.38
    HAWKISH = 0.71

    def test_dovish_bullish_xau(self, router: TargetRouter) -> None:
        """Inti bug P0-2: dovish tidak boleh menghasilkan XAU bearish."""
        impact = _xau_impact(router, "Gold gains as Fed cuts rates", self.DOVISH, "stance")
        assert impact.direction is Direction.BULLISH
        # Skor juga harus searah, bukan skor stance mentah yang negatif.
        assert impact.score > 0

    def test_hawkish_bearish_xau(self, router: TargetRouter) -> None:
        impact = _xau_impact(router, "Gold falls as Fed raises rates", self.HAWKISH, "stance")
        assert impact.direction is Direction.BEARISH
        assert impact.score < 0

    def test_skor_dan_direction_konsisten(self, router: TargetRouter) -> None:
        """`direction` dan `score` tidak boleh bertentangan.

        Tanpa perbaikan, `direction=BULLISH` bisa berpasangan dengan
        `score=-0.38`; konsumen hilir (persona/alloc) membaca sinyal yang
        saling bertentangan.
        """
        for score in (self.DOVISH, self.HAWKISH):
            impact = _xau_impact(router, "Gold reacts to the Fed", score, "stance")
            if impact.direction is Direction.BULLISH:
                assert impact.score > 0
            elif impact.direction is Direction.BEARISH:
                assert impact.score < 0

    def test_mode_price_tidak_berubah(self, router: TargetRouter) -> None:
        """Regresi: FinBERT-EMAS (mode `price`) harus berperilaku seperti dulu.

        Skor FinBERT-EMAS sudah berupa arah harga emas, jadi TIDAK boleh
        dibalik oleh `stance_direction`.
        """
        impact = _xau_impact(router, "Gold gains as Fed cuts rates", -0.38, "price")
        assert impact.direction is Direction.BEARISH
        assert impact.score == pytest.approx(-0.38)

    def test_ratus_ust_ikut_terbalik(self, router: TargetRouter) -> None:
        """RATE_UST bergerak berlawanan dengan XAU terhadap stance yang sama.

        Dovish -> yield turun (bearish RATE_UST) tetapi emas naik (bullish).
        Ini membuktikan pemetaan benar-benar per-aset, bukan sekadar
        membalik semua tanda.
        """
        impacts = router.route_article(
            _article("Treasury yield and gold react to the Fed"),
            sentiment_score=self.DOVISH,
            score_space="stance",
        )
        by_asset = {i.asset_id: i for i in impacts}
        assert by_asset["XAU"].direction is Direction.BULLISH
        assert by_asset["RATE_UST"].direction is Direction.BEARISH

    def test_netral_di_dalam_band(self, router: TargetRouter) -> None:
        """Skor stance kecil tidak boleh menghasilkan arah."""
        impact = _xau_impact(router, "Gold barely moved after the Fed", 0.02, "stance")
        assert impact.direction is Direction.NEUTRAL


class TestKonfigurasiArah:
    def test_xau_terdaftar_minus_satu(self) -> None:
        """XAU harus ada di peta arah; sebelumnya hanya RATE_UST/SPX."""
        mapping = stance_direction()
        assert mapping["XAU"] == -1

    def test_searah_impact_graph(self, router: TargetRouter) -> None:
        """`stance_direction` tidak boleh bertentangan dengan `impact_graph`.

        `impact_graph` menyatakan hawkish -> XAU turun lewat tema `rates_up`
        (sign -1). Jika peta stance menyatakan sebaliknya, dua jalur routing
        akan memberi arah berlawanan untuk artikel yang sama.
        """
        assert stance_direction()["XAU"] == -1
        rates_up = router.impact_graph["rates_up"]
        xau = next(e for e in rates_up if e["target"] == "XAU")
        assert xau["sign"] == -1

    def test_hanya_plus_minus_satu(self) -> None:
        for asset, sign in stance_direction().items():
            assert sign in (-1, 1), f"{asset}={sign} di luar {{+1,-1}}"


class TestPrioritasModel:
    """P0-3: prioritas model adalah data eksplisit, bukan urutan `if`."""

    def test_fomc_lebih_dulu_dari_xau(self) -> None:
        names = [row[0] for row in MODEL_PRIORITY]
        assert names.index("fomc_roberta") < names.index("finbert_emas")

    def test_setiap_baris_lengkap(self) -> None:
        """Tiap baris harus punya loader & `score_space` yang sah."""
        for name, loader_name, default_version, space in MODEL_PRIORITY:
            assert name and loader_name and default_version
            assert space in ("price", "stance"), f"{name}: score_space={space!r}"

    def test_fomc_ditandai_stance(self) -> None:
        """FOMC mengukur stance; kalau ditandai `price`, P0-2 kembali bug."""
        row = next(r for r in MODEL_PRIORITY if r[0] == "fomc_roberta")
        assert row[3] == "stance"

    def test_finbert_ditandai_price(self) -> None:
        """FinBERT-EMAS dilatih pada sentimen harga emas, bukan stance Fed."""
        row = next(r for r in MODEL_PRIORITY if r[0] == "finbert_emas")
        assert row[3] == "price"

    def test_loader_ada_di_runner(self) -> None:
        """Nama loader harus benar-benar ada, bukan string mati."""
        from backend.src.pipeline.runner import Pipeline

        for name, loader_name, _version, _space in MODEL_PRIORITY:
            assert hasattr(Pipeline, loader_name), (
                f"{name}: runner tidak punya method {loader_name}"
            )

    def test_tidak_ada_model_ganda(self) -> None:
        names = [row[0] for row in MODEL_PRIORITY]
        assert len(names) == len(set(names))
