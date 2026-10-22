"""Tests for T-2: CLI lengkap (FR-14) dan ekspor laporan.

Menekankan dua hal yang mudah rusak tanpa terlihat:
- `report` HARUS benar-benar memuat angka statistik (parameter `stats` dulu
  diterima tapi tidak pernah dipakai -- laporan tampak jadi, isinya kosong).
- perintah bertahap harus bisa dijalankan tanpa menyentuh DB saat `--dry-run`.
"""

from datetime import date

import pytest

from backend.src.cli import build_parser, main
from backend.src.report.exporter import ReportExporter
from backend.src.schema import DailySentiment, StatResult
from backend.src.store.db import Database


@pytest.fixture()
def db(tmp_path):
    d = Database(tmp_path / "cli.db")
    d.init_schema()
    return d


def _stat(asset="SPX", test="ols", est=0.0123, p=0.0004, lag=1):
    return StatResult(
        run_id="run01",
        asset_id=asset,
        test=test,
        market_metric="return",
        lag=lag,
        estimate=est,
        ci_low=-0.01,
        ci_high=0.03,
        p_value=p,
        p_adjusted=min(1.0, p * 2),
        n_obs=250,
        period_start=date(2023, 1, 2),
        period_end=date(2023, 12, 29),
        params_json="{}",
        code_version="v0.5.0",
    )


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


def test_parser_has_all_expected_commands():
    """Semua perintah FR-14 harus terdaftar."""
    help_text = build_parser().format_help()
    for cmd in [
        "seed",
        "prices",
        "pipeline",
        "status",
        "clean",
        "score",
        "aggregate",
        "stats",
        "report",
    ]:
        assert cmd in help_text, f"perintah `{cmd}` hilang dari CLI"


def test_parser_accepts_stats_flags():
    args = build_parser().parse_args(["stats", "--max-lag", "7", "--dry-run"])
    assert args.max_lag == 7
    assert args.dry_run is True


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------


def test_report_html_actually_contains_statistics(db, tmp_path):
    """Regresi: laporan pernah mengabaikan argumen `stats` sepenuhnya."""
    db.save_stat(_stat())
    db.save_stat(_stat(test="granger", est=7.42, p=0.031, lag=2))

    out = ReportExporter(tmp_path).export_html_report(
        universe=[{"asset_id": "SPX", "name": "S&P 500", "track": "market",
                   "asset_class": "equity", "session_close": "16:00"}],
        stats=[
            {"asset_id": "SPX", "test": "ols", "lag": 1, "estimate": 0.0123,
             "ci_low": -0.01, "ci_high": 0.03, "p_value": 0.0004,
             "p_adjusted": 0.0008, "n_obs": 250},
            {"asset_id": "SPX", "test": "granger", "lag": 2, "estimate": 7.42,
             "ci_low": None, "ci_high": None, "p_value": 0.031,
             "p_adjusted": 0.062, "n_obs": 250},
        ],
        allocations={},
    )
    html = out.read_text(encoding="utf-8")

    assert "SPX" in html
    assert "granger" in html
    assert "0.01230" in html, "estimasi OLS harus tercetak di laporan"
    assert "7.42000" in html, "statistik F Granger harus tercetak"
    assert "250" in html, "jumlah observasi harus tercetak"


def test_report_marks_significant_rows(db, tmp_path):
    """Baris dengan p(BH) < 0,05 harus ditandai agar terbaca sekilas."""
    out = ReportExporter(tmp_path).export_html_report(
        universe=[],
        stats=[
            {"asset_id": "XAU", "test": "ols", "lag": 0, "estimate": 0.02,
             "ci_low": 0.01, "ci_high": 0.03, "p_value": 0.001,
             "p_adjusted": 0.004, "n_obs": 300},
        ],
        allocations={},
    )
    html = out.read_text(encoding="utf-8")
    assert "sig-strong" in html or "sig" in html


def test_report_handles_missing_ci_gracefully(tmp_path):
    """Granger tidak punya CI; laporan tidak boleh mencetak 'None'."""
    out = ReportExporter(tmp_path).export_html_report(
        universe=[],
        stats=[
            {"asset_id": "SPX", "test": "granger", "lag": 1, "estimate": 5.0,
             "ci_low": None, "ci_high": None, "p_value": 0.2,
             "p_adjusted": 0.3, "n_obs": 200},
        ],
        allocations={},
    )
    html = out.read_text(encoding="utf-8")
    assert "None" not in html
    assert "&mdash;" in html


def test_report_without_stats_shows_hint(tmp_path):
    """Universe kosong + tanpa statistik harus memberi petunjuk, bukan tabel kosong."""
    out = ReportExporter(tmp_path).export_html_report(
        universe=[], stats=[], allocations={}
    )
    html = out.read_text(encoding="utf-8")
    assert "cli stats" in html, "harus menyarankan menjalankan `stats`"


# ---------------------------------------------------------------------------
# stats & status (tanpa jaringan)
# ---------------------------------------------------------------------------


def test_stats_reports_insufficient_pairs_without_crashing(db, tmp_path, capsys):
    """Dengan data minim, `stats` harus berhenti dengan pesan jelas (exit 0)."""
    db.seed_asset_master()
    code = main(["--db", str(db.db_path), "stats", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "0 baris statistik" in out or "hari berpasangan" in out


def test_status_runs(db, capsys):
    code = main(["--db", str(db.db_path), "status"])
    assert code == 0


# ==========================================================
# S-3: ParquetStore bukan lagi kode mati
# ==========================================================


def test_export_command_writes_parquet(db, tmp_path, capsys):
    """`export` harus benar-benar memanggil ParquetStore dan menghasilkan file.

    S-3: `ParquetStore` berfungsi tetapi nol pemanggil. Test ini mengunci
    bahwa ia kini terpasang di jalur nyata, bukan hanya tersedia.
    """
    pytest.importorskip("pyarrow")
    import pandas as pd

    db.seed_asset_master()
    db.save_daily_sentiment(
        DailySentiment(
            asset_id="XAU",
            date=date(2026, 10, 1),
            score_mean=0.3,
            score_weighted=0.3,
            n_articles=2,
            n_sources=1,
            has_news=True,
        )
    )

    out = tmp_path / "pq"
    code = main(["--db", str(db.db_path), "export", "--out", str(out)])
    assert code == 0

    file = out / "daily_sentiment.parquet"
    assert file.exists(), "ParquetStore tidak menulis apa pun"
    df = pd.read_parquet(file)
    assert len(df) == 1
    assert df.iloc[0]["asset_id"] == "XAU"


def test_export_round_trips_values(db, tmp_path):
    """Nilai harus selamat melewati Parquet, bukan hanya filenya ada."""
    pytest.importorskip("pyarrow")
    import pandas as pd

    db.seed_asset_master()
    db.save_daily_sentiment(
        DailySentiment(
            asset_id="SPX",
            date=date(2026, 10, 2),
            score_mean=-0.42,
            score_weighted=-0.40,
            n_articles=7,
            n_sources=3,
            has_news=True,
        )
    )
    out = tmp_path / "pq"
    main(["--db", str(db.db_path), "export", "--out", str(out)])

    df = pd.read_parquet(out / "daily_sentiment.parquet")
    assert df.iloc[0]["score_mean"] == pytest.approx(-0.42)
    assert df.iloc[0]["n_articles"] == 7


def test_export_on_empty_db_does_not_crash(db, tmp_path, capsys):
    """DB kosong: lewati tabel kosong, jangan menulis file palsu."""
    pytest.importorskip("pyarrow")
    out = tmp_path / "pq"
    code = main(["--db", str(db.db_path), "export", "--out", str(out)])
    assert code == 0
    assert not (out / "daily_sentiment.parquet").exists()


def test_export_includes_news_horizon(db, tmp_path):
    """S-5 + S-3: horizon yang baru disimpan ikut terekspor."""
    pytest.importorskip("pyarrow")
    import pandas as pd

    from backend.src.schema import Basis, Direction, EvidenceSpan, NewsHorizon, TargetImpact

    db.seed_asset_master()
    db.save_impact(
        TargetImpact(
            article_id="e1",
            asset_id="XAU",
            direction=Direction.BULLISH,
            score=0.5,
            confidence=0.8,
            basis=Basis.EXPLICIT,
            themes=[],
            evidence=[EvidenceSpan(quote="Gold climbs", start=0, end=12)],
            news_horizon=NewsHorizon.MEDIUM,
            model_version="fusion-v1",
        )
    )
    out = tmp_path / "pq"
    main(["--db", str(db.db_path), "export", "--out", str(out)])

    df = pd.read_parquet(out / "impacts.parquet")
    assert "news_horizon" in df.columns
    assert df.iloc[0]["news_horizon"] == "medium"
