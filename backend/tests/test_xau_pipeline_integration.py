"""Test integrasi Pipeline Runner dengan model spesialis FinBERT-EMAS (FR-6).

Sebelum berkas ini, `model_router.py` mengembalikan track `finbert_emas`
untuk artikel emas tetapi `runner.py` tidak punya cabang untuk memuatnya.
Akibatnya artikel emas tetap diskor baseline TF-IDF generik dan tidak ada
test yang menangkapnya — FR-6 tampak selesai padahal tidak tersambung.

Yang diverifikasi:
1. `xau_model` lazy: tidak dimuat sebelum ada artikel emas.
2. Artikel emas memakai model XAU dan `model_version` ikut tercatat.
3. Tanpa bobot terlatih, `load_xau_model()` mengembalikan None sehingga
   pipeline turun ke baseline (bukan crash).
4. Artikel non-emas tidak menyentuh model XAU.
5. Ambang netral berasal dari `data/sentiment_config.yaml`, bukan literal.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.src.pipeline.runner import Pipeline
from backend.src.schema import Article, ArticleSentiment, Direction, Lang, ModelProbs, Tone
from backend.src.store.db import Database
from model.common.sentiment_config import FALLBACK, neutral_band

XAU_WEIGHTS_DIR = Path("model/xau/weights/finbert_gold")


def _create_article(
    article_id: str,
    title: str,
    body: str = "",
    source: str = "kitco_rss",
) -> Article:
    return Article(
        article_id=article_id,
        source=source,
        url=f"https://example.com/news/{article_id}",
        title=title,
        body=body,
        language=Lang.EN,
        published_at=datetime(2026, 10, 23, 10, 0, 0, tzinfo=timezone.utc),
        fetched_at=datetime(2026, 10, 23, 10, 5, 0, tzinfo=timezone.utc),
        effective_trading_date={},
    )


def _mock_xau_model(article_id: str, tone: Tone = Tone.POSITIVE) -> MagicMock:
    """Model XAU deterministik untuk mengisolasi test dari bobot 440MB."""
    mock = MagicMock()
    mock.model_name = "finbert_gold"
    mock.model_version = "finbert-gold-v1.0"
    mock.score_article.return_value = ArticleSentiment(
        article_id=article_id,
        tone=tone,
        score=0.72,
        probs=[
            ModelProbs(
                model="finbert_gold",
                model_version="finbert-gold-v1.0",
                p_pos=0.82,
                p_neu=0.10,
                p_neg=0.08,
            )
        ],
    )
    return mock


def test_lazy_loading_xau_model(temp_db: Database) -> None:
    """Model XAU tidak boleh dimuat saat inisialisasi."""
    pipeline = Pipeline(db_path=temp_db.db_path)
    assert pipeline.xau_model is None, "xau_model harus lazy (None saat inisialisasi)"


def test_tanpa_bobot_xau_turun_ke_baseline(temp_db: Database) -> None:
    """Tanpa bobot terlatih, load_xau_model mengembalikan None, bukan meledak.

    Inilah kondisi nyata repo saat ini: FR-6 terpasang tetapi bobot belum
    dilatih. Pipeline wajib tetap jalan memakai baseline.
    """
    if XAU_WEIGHTS_DIR.exists():
        pytest.skip("Bobot XAU sudah ada; kasus 'belum dilatih' tidak berlaku")

    pipeline = Pipeline(db_path=temp_db.db_path)
    assert pipeline.load_xau_model() is None


def test_artikel_emas_memakai_model_xau(temp_db: Database) -> None:
    """Artikel emas dialihkan ke model XAU dan jejaknya tercatat di DB."""
    pipeline = Pipeline(db_path=temp_db.db_path)
    pipeline.xau_model = _mock_xau_model("art-xau-001")

    article = _create_article(
        "art-xau-001",
        "Gold price rallies as dollar weakens",
        "Gold surged to a record high as the dollar weakened and demand rose.",
    )
    temp_db.save_articles([article])

    impacts, _stats = pipeline.score_and_route([article], dry_run=False)

    pipeline.xau_model.score_article.assert_called_once()

    assert impacts, "Artikel emas harus menghasilkan minimal satu dampak"
    xau_impacts = [imp for imp in impacts if imp.asset_id == "XAU"]
    assert len(xau_impacts) == 1, "Harus ada tepat 1 dampak untuk XAU"

    xau_imp = xau_impacts[0]
    assert xau_imp.direction == Direction.BULLISH
    assert xau_imp.score > 0
    assert xau_imp.model_version == "finbert-gold-v1.0"
    assert xau_imp.routed_from is not None
    assert "finbert_emas" in xau_imp.routed_from

    xau_row = temp_db.get_impact_for_article("art-xau-001", "XAU")
    assert xau_row is not None
    assert xau_row["direction"] == "bullish"

    db_sentiments = temp_db.query_sentiments("art-xau-001")
    assert len(db_sentiments) > 0
    assert db_sentiments[0]["model"] == "finbert_gold"
    assert db_sentiments[0]["model_version"] == "finbert-gold-v1.0"


def test_artikel_non_emas_tidak_menyentuh_model_xau(temp_db: Database) -> None:
    """Artikel non-emas tidak boleh memicu pemuatan model XAU."""
    pipeline = Pipeline(db_path=temp_db.db_path)
    pipeline.xau_model = _mock_xau_model("art-lain")

    article = _create_article(
        "art-lain",
        "Cuaca cerah di Jakarta sepanjang pekan",
        "Tidak ada berita pasar pada artikel ini.",
        source="umum",
    )
    temp_db.save_articles([article])

    pipeline.score_and_route([article], dry_run=False)

    pipeline.xau_model.score_article.assert_not_called()


def test_ambang_netral_dari_config_bukan_literal() -> None:
    """RULES.md: ambang wajib di config, dan berkasnya harus konsisten."""
    config_path = Path("data/sentiment_config.yaml")
    assert config_path.exists(), "data/sentiment_config.yaml wajib ada (RULES.md)"

    nilai = neutral_band(config_path)
    assert 0.0 <= nilai <= 1.0
    assert nilai == FALLBACK["neutral_band"], (
        "Nilai di YAML harus sama dengan FALLBACK agar perilaku tidak "
        "berubah ketika berkas tidak ditemukan."
    )


def test_ambang_netral_fallback_bila_config_hilang(tmp_path: Path) -> None:
    """Berkas hilang tidak boleh mematikan model; dipakai nilai bawaan."""
    assert neutral_band(tmp_path / "tidak-ada.yaml") == FALLBACK["neutral_band"]


def test_ambang_netral_menolak_nilai_tidak_masuk_akal(tmp_path: Path) -> None:
    """`neutral_band` di luar [0, 1] diabaikan agar skor tidak selalu netral."""
    cfg = tmp_path / "aneh.yaml"
    cfg.write_text("decision:\n  neutral_band: 5.0\n", encoding="utf-8")
    assert neutral_band(cfg) == FALLBACK["neutral_band"]
