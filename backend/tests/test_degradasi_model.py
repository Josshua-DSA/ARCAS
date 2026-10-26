"""Test untuk jalur degradasi model (audit P1-1).

Masalah yang dikunci di sini: bila bobot FOMC-RoBERTa tidak ada, pipeline
jatuh ke baseline TF-IDF. Sebelumnya itu terjadi DIAM-DIAM -- hanya
`logger.warning`, tidak ada jejak di output run. Akibatnya laporan bisa
menyajikan angka baseline (57,98%) seolah-olah hasil model spesialis
(86,87%) tanpa pembaca bisa tahu.

Test ini memastikan degradasi selalu terlihat di `PipelineStats.errors`,
yang dicetak oleh `PipelineStats.ringkas()`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.src.pipeline.runner import Pipeline
from backend.src.schema import Article, Lang


@pytest.fixture()
def pipeline(temp_db) -> Pipeline:
    return Pipeline(db_path=temp_db.db_path)


def _artikel(article_id: str = "art-p11") -> Article:
    from datetime import UTC, datetime

    return Article(
        article_id=article_id,
        source="federalreserve.gov",
        url=f"https://example.com/{article_id}",
        title="FOMC raises rates by 25 basis points",
        body="The Federal Reserve raised interest rates and signaled tightening ahead.",
        language=Lang.EN,
        published_at=datetime(2024, 1, 31, 19, 0, tzinfo=UTC),
        fetched_at=datetime.now(UTC),
    )


class TestDegradasiModelTerlihat:
    def test_gagal_muat_dicatat_dan_bukan_hanya_log(self, pipeline: Pipeline) -> None:
        """Kegagalan memuat RoBERTa harus muncul di ringkasan, bukan cuma log."""
        with patch(
            "model.fomc.src.model.FOMCRoBERTaSentiment",
            side_effect=RuntimeError("bobot tidak ditemukan"),
        ):
            model = pipeline.load_fomc_model()

        assert model is None
        assert pipeline._degradasi, "Degradasi tidak dicatat sama sekali"
        pesan = " ".join(pipeline._degradasi)
        assert "FOMC" in pesan
        assert "baseline TF-IDF" in pesan
        assert "bobot tidak ditemukan" in pesan

    def test_degradasi_muncul_di_stats_errors(self, pipeline: Pipeline) -> None:
        """`score_and_route` harus meneruskan degradasi ke PipelineStats.errors.

        Inilah yang membuat `ringkas()` menampilkannya; tanpa ini pengguna
        hanya melihat logger (mudah terlewat di CI / cron).
        """
        with patch(
            "model.fomc.src.model.FOMCRoBERTaSentiment",
            side_effect=RuntimeError("bobot tidak ditemukan"),
        ):
            pipeline.load_fomc_model()

        _impacts, stats = pipeline.score_and_route([_artikel()], dry_run=True)

        assert any("DEGRADASI" in e or "baseline TF-IDF" in e for e in stats.errors), (
            f"Degradasi tidak masuk ke stats.errors: {stats.errors}"
        )

    def test_deg_ditampilkan_oleh_ringkas(self, pipeline: Pipeline) -> None:
        """`ringkas()` (dipakai CLI) wajib menyebut jumlah error.

        Degradasi yang tidak terlihat di output CLI sama saja dengan diam.
        """
        with patch(
            "model.fomc.src.model.FOMCRoBERTaSentiment",
            side_effect=RuntimeError("bobot tidak ditemukan"),
        ):
            pipeline.load_fomc_model()

        _impacts, stats = pipeline.score_and_route([_artikel()], dry_run=True)
        ringkasan = stats.ringkas()

        assert "error" in ringkasan.lower()
        # Jumlah error harus > 0 karena degradasi ikut terhitung
        assert int(ringkasan.rsplit(":", 1)[-1].strip()) >= 1

    def test_tanpa_torch_dicatat_sebagai_degradasi(self, pipeline: Pipeline) -> None:
        """Ketiadaan torch juga harus eksplisit, bukan fallback senyap."""
        with patch("importlib.util.find_spec", return_value=None):
            model = pipeline.load_fomc_model()

        assert model is None
        pesan = " ".join(pipeline._degradasi)
        assert "torch" in pesan.lower() or "transformers" in pesan.lower()

    def test_tidak_ada_degradasi_bila_model_berhasil(self, pipeline: Pipeline) -> None:
        """Jalur sukses tidak boleh menghasilkan peringatan palsu.

        Peringatan yang selalu muncul akan diabaikan orang, sehingga
        peringatan yang penting kehilangan makna.
        """
        _impacts, stats = pipeline.score_and_route([_artikel()], dry_run=True)

        assert pipeline._degradasi == []
        assert not any("DEGRADASI" in e for e in stats.errors)


class TestFetchWeightsScript:
    """Memastikan skrip verifikasi bobot ada dan bisa dijalankan."""

    def test_skrip_ada(self) -> None:
        root = Path(__file__).resolve().parents[2]
        skrip = root / "scripts" / "fetch_weights.py"
        assert skrip.exists(), "scripts/fetch_weights.py hilang (audit P1-1)"

    def test_verify_only_mengembalikan_nol_untuk_bobot_terpasang(self) -> None:
        """`--verify-only` harus lulus pada bobot yang sehat.

        Dilewati bila bobot tidak ada di mesin ini (mis. CI tanpa bobot),
        karena skrip ini justru dipakai untuk mengambilnya.
        """
        root = Path(__file__).resolve().parents[2]
        sys.path.insert(0, str(root / "scripts"))
        try:
            from fetch_weights import CHECKSUMS, verify_local
        finally:
            sys.path.pop(0)

        if not (root / CHECKSUMS["xau"]["local_dir"]).exists():
            pytest.skip("Bobot XAU tidak ada di mesin ini")

        masalah = verify_local("xau", CHECKSUMS["xau"])
        assert masalah == [], f"Verifikasi bobot XAU gagal: {masalah}"
