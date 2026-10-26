"""Smoke test yang membuktikan FOMC-RoBERTa BENAR-BENAR dipakai.

Audit P1-4: seluruh `test_fomc_pipeline_integration.py` memakai `MagicMock`
untuk model, sehingga tidak ada satu pun test yang memverifikasi
`probs[0].model == "fomc_roberta"`. Akibatnya suite selalu hijau baik
RoBERTa hidup maupun mati -- dan itulah sebabnya bug "RoBERTa tidak pernah
aktif" bisa lolos.

Test ini memuat model nyata, jadi ditandai `slow` + `network` dan
DIKELUARKAN dari suite default (lihat `addopts` di pyproject.toml). Jalankan
secara eksplisit:

    pytest -m slow backend/tests/test_fomc_roberta_real.py

Model yang diuji bukan mock: bobot RoBERTa ~1,3 GB dimuat dari cache
HuggingFace (atau diunduh bila belum ada).
"""

from __future__ import annotations

import pytest

from model.fomc.src.model import FOMCRoBERTaSentiment

pytestmark = [pytest.mark.slow, pytest.mark.network]


@pytest.fixture(scope="module")
def roberta() -> FOMCRoBERTaSentiment:
    """Muat model nyata sekali per modul (pemuatan ~1,3 GB tidak murah)."""
    try:
        model = FOMCRoBERTaSentiment(lazy_load=False)
    except Exception as exc:  # pragma: no cover - lingkungan tanpa bobot/jaringan
        pytest.skip(f"Model FOMC-RoBERTa tidak dapat dimuat: {exc}")
    return model


class TestRoBERTaBenarBenarDipakai:
    def test_model_name_bukan_baseline(self, roberta: FOMCRoBERTaSentiment) -> None:
        """Inti P1-4: nama model harus `fomc_roberta`, bukan baseline.

        Bila RoBERTa diam-diam jatuh ke baseline TF-IDF, assertion ini gagal
        sedangkan seluruh test ber-mock tetap hijau.
        """
        assert roberta.model_name == "fomc_roberta"
        assert roberta.model_version == "fomc-roberta-v1.0"

    def test_predict_probs_mengembalikan_label_model_roberta(
        self, roberta: FOMCRoBERTaSentiment
    ) -> None:
        """Label pada output harus berasal dari model nyata, bukan default."""
        probs = roberta.predict_probs(
            ["The Federal Reserve raised interest rates by 25 basis points."]
        )

        assert len(probs) == 1
        assert probs[0].model == "fomc_roberta"
        assert probs[0].model_version == "fomc-roberta-v1.0"

    def test_probabilitas_valid_dan_menjumlah_satu(
        self, roberta: FOMCRoBERTaSentiment
    ) -> None:
        """Invarian output: tiap probabilitas di [0,1] dan totalnya 1.0."""
        texts = [
            "The Federal Reserve raised interest rates by 25 basis points.",
            "Powell signaled patience as inflation continues to cool.",
        ]
        probs = roberta.predict_probs(texts)

        assert len(probs) == 2
        for p in probs:
            assert 0.0 <= p.p_pos <= 1.0
            assert 0.0 <= p.p_neu <= 1.0
            assert 0.0 <= p.p_neg <= 1.0
            assert p.p_pos + p.p_neu + p.p_neg == pytest.approx(1.0, abs=1e-3)

    def test_kalimat_hawkish_condong_positif(self, roberta: FOMCRoBERTaSentiment) -> None:
        """Sanity semantik: kalimat pengetatan moneter -> p_pos tertinggi.

        Ini bukan jaminan akurasi (model bisa saja salah), tetapi model yang
        aktif seharusnya memberi sinyal masuk akal. Bila ini gagal sementara
        test label di atas lulus, kemungkinan pemetaan label Hawkish/Dovish
        terbalik -- bug yang pernah terjadi di track ini.
        """
        probs = roberta.predict_probs(
            ["The Federal Reserve raised interest rates by 75 basis points "
             "and signaled further tightening to fight inflation."]
        )[0]

        assert probs.p_pos > probs.p_neg, (
            f"Kalimat hawkish seharusnya condong positif: "
            f"p_pos={probs.p_pos} p_neu={probs.p_neu} p_neg={probs.p_neg}"
        )

    def test_batch_konsisten_dengan_single(self, roberta: FOMCRoBERTaSentiment) -> None:
        """Prediksi satu per satu harus sama dengan prediksi batch.

        Menangkap bug padding/masking pada tokenizer, yang gejalanya persis
        seperti ini: hasil berubah tergantung isi batch.
        """
        texts = [
            "The Federal Reserve raised interest rates by 25 basis points.",
            "Powell signaled patience as inflation continues to cool.",
        ]
        batch = roberta.predict_probs(texts)
        single = [roberta.predict_probs([t])[0] for t in texts]

        for b, s in zip(batch, single):
            assert b.p_pos == pytest.approx(s.p_pos, abs=1e-3)
            assert b.p_neu == pytest.approx(s.p_neu, abs=1e-3)
            assert b.p_neg == pytest.approx(s.p_neg, abs=1e-3)


class TestPipelineMemakaiRoBERTa:
    """Membuktikan model nyata sampai ke output pipeline, bukan hanya wrapper."""

    def test_artikel_fomc_diskor_oleh_roberta(self) -> None:
        """Pipeline harus melabeli sentimen FOMC dengan `fomc_roberta`.

        Ini menutup celah yang dilaporkan audit: `test_fomc_pipeline_integration.py`
        memakai MagicMock, jadi tidak pernah membuktikan model nyata dipakai.
        """
        import tempfile
        from datetime import UTC, datetime
        from pathlib import Path

        from backend.src.pipeline.runner import Pipeline
        from backend.src.schema import Article, Lang

        with tempfile.TemporaryDirectory() as d:
            pipeline = Pipeline(db_path=Path(d) / "smoke.db")
            pipeline.db.init_schema()
            # Pastikan model RoBERTa NYATA yang dimuat, bukan baseline.
            pipeline.load_fomc_model = lambda: FOMCRoBERTaSentiment(lazy_load=False)  # type: ignore[method-assign]

            article = Article(
                article_id="smoke-roberta-1",
                source="federalreserve.gov",
                url="https://example.com/smoke-roberta-1",
                title="FOMC raises rates by 50 basis points",
                body=(
                    "The Federal Reserve raised interest rates by 50 basis points "
                    "and signaled further tightening to fight inflation."
                ),
                language=Lang.EN,
                published_at=datetime(2024, 1, 31, 19, 0, tzinfo=UTC),
                fetched_at=datetime.now(UTC),
            )

            impacts, _stats = pipeline.score_and_route([article], dry_run=True)

            assert impacts, "Pipeline tidak menghasilkan sentimen untuk artikel FOMC"

            # Inti P1-4: versi model pada impact harus menandai RoBERTa, dan
            # jejak routing harus menyebut modelnya. Bila RoBERTa diam-diam
            # jatuh ke baseline, dua assertion ini gagal.
            versions = {imp.model_version for imp in impacts}
            assert "fomc-roberta-v1.0" in versions, (
                f"Pipeline jatuh ke model lain: {versions}. Ini berarti RoBERTa "
                "tidak aktif meski tidak ada error yang dilaporkan."
            )
            routed = " ".join(imp.routed_from or "" for imp in impacts)
            assert "fomc_roberta" in routed, (
                f"routed_from tidak menyebut fomc_roberta: {routed!r}"
            )
