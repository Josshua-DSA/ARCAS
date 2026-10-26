"""Test integrasi end-to-end: raw_articles -> articles -> impacts -> daily_sentiment.

Test inilah yang seharusnya menangkap AUDIT K-1. Semua test lain menguji
komponen satu per satu dengan `tmpdir`, sehingga sambungannya tidak pernah
diuji. Test ini sengaja memakai database nyata sementara dan model nyata.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.src.pipeline import Pipeline

MODEL_PATH = Path("model/common/baseline_tfidf.joblib")
requires_model = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason="latih dulu: python -m model.common.train_baseline",
)

ARTIKEL_UJI = [
    # Jelas emas & bullish
    ("Gold rallies as Fed signals rate cuts ahead", "rss:kitco", "XAU"),
    # Jelas emas & bearish
    ("Gold falls sharply as dollar strengthens", "finnhub:Reuters", "XAU"),
    # Menyebut S&P 500 eksplisit
    ("S&P 500 closes at record high on tech rally", "finnhub:CNBC", "SPX"),
    # Berita tanpa target sama sekali
    ("Local weather forecast for Jakarta tomorrow", "rss:generic", "XAU"),
]


def _iso(dt: datetime) -> str:
    return dt.isoformat()


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Database kosong dengan skema lengkap + beberapa raw_articles."""
    from backend.src.store.db import Database

    path = tmp_path / "test.db"
    db = Database(path)
    db.init_schema()

    now = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    with db.get_connection() as conn:
        for judul, sumber, target in ARTIKEL_UJI:
            conn.execute(
                """
                INSERT INTO raw_articles (
                    source, url, title, body, published_at, fetched_at,
                    query_target, vendor_sentiment, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sumber,
                    f"https://example.com/{abs(hash(judul))}",
                    judul,
                    # Body harus berbahasa Inggris: sebelumnya fixture memakai
                    # template Indonesia ("Detail tambahan untuk tubuh
                    # artikel.") yang membuat detektor lingua — dengan benar —
                    # menandai artikel ini `id`, sehingga pipeline (yang
                    # melewati artikel non-Inggris) tidak menulis sentimen.
                    f"{judul}. Additional detail for the article body.",
                    _iso(now),
                    _iso(now),
                    target,
                    None,
                    None,
                ),
            )
    return path


def _count(path: Path, table: str) -> int:
    with sqlite3.connect(path) as conn:
        return conn.execute(f"SELECT count(*) FROM {table};").fetchone()[0]


@requires_model
def test_pipeline_mengisi_semua_tabel(db_path: Path) -> None:
    """Satu kali jalan harus mengisi seluruh rantai tabel."""
    pipe = Pipeline(db_path=db_path)
    stats = pipe.run(limit=100, dry_run=False)

    assert stats.raw_dibaca == len(ARTIKEL_UJI)
    assert stats.errors == []
    assert stats.artikel_tertulis == len(ARTIKEL_UJI)

    # Inilah inti K-1: sebelumnya tabel-tabel ini tetap kosong.
    assert _count(db_path, "articles") == len(ARTIKEL_UJI)
    assert _count(db_path, "sentiments") > 0
    assert _count(db_path, "impacts") > 0
    assert _count(db_path, "article_targets") > 0
    assert _count(db_path, "daily_sentiment") > 0
    assert _count(db_path, "asset_master") == 3


@requires_model
def test_pipeline_idempoten(db_path: Path) -> None:
    """Menjalankan dua kali tidak boleh menggandakan baris."""
    pipe = Pipeline(db_path=db_path)
    pipe.run(limit=100)
    setelah_pertama = {t: _count(db_path, t) for t in ("articles", "impacts", "daily_sentiment")}

    pipe.run(limit=100)
    setelah_kedua = {t: _count(db_path, t) for t in ("articles", "impacts", "daily_sentiment")}

    assert setelah_pertama == setelah_kedua


@requires_model
def test_dry_run_tidak_menulis(db_path: Path) -> None:
    """--dry-run menghitung tapi tidak menyentuh database."""
    pipe = Pipeline(db_path=db_path)
    stats = pipe.run(limit=100, dry_run=True)

    assert stats.raw_dibaca == len(ARTIKEL_UJI)
    assert _count(db_path, "articles") == 0
    assert _count(db_path, "impacts") == 0


@requires_model
def test_berita_tanpa_target_tidak_dipaksa_bertarget(db_path: Path) -> None:
    """Artikel cuaca tidak boleh menghasilkan impact apa pun."""
    pipe = Pipeline(db_path=db_path)
    stats = pipe.run(limit=100, dry_run=False)

    assert stats.tanpa_target >= 1

    with sqlite3.connect(db_path) as conn:
        baris = conn.execute(
            "SELECT a.article_id FROM articles a WHERE a.title LIKE 'Local weather%';"
        ).fetchall()
    assert len(baris) == 1
    artikel_id = baris[0][0]

    with sqlite3.connect(db_path) as conn:
        n = conn.execute(
            "SELECT count(*) FROM impacts WHERE article_id = ?;", (artikel_id,)
        ).fetchone()[0]
    assert n == 0, "berita non-pasar tidak boleh dipaksa punya impact"


@requires_model
def test_n_sources_menghitung_sumber_unik(db_path: Path) -> None:
    """n_sources harus mencerminkan jumlah sumber unik, bukan konstanta 1."""
    from datetime import date

    from backend.src.aggregate.daily import DailyAggregator
    from backend.src.schema import Basis, Direction, EvidenceSpan, TargetImpact

    impacts = [
        TargetImpact(
            article_id=f"a{i}",
            asset_id="XAU",
            direction=Direction.BULLISH,
            score=0.5,
            confidence=0.9,
            basis=Basis.EXPLICIT,
            themes=[],
            evidence=[EvidenceSpan(quote="gold", start=0, end=4)],
            flags=[],
            model_version="v1",
        )
        for i in range(3)
    ]
    hasil = DailyAggregator.aggregate_for_asset_date(
        asset_id="XAU",
        trading_date=date(2026, 10, 20),
        impacts=impacts,
        sources=["reuters", "reuters", "cnbc"],
    )
    assert hasil.n_sources == 2, "dua sumber unik dari tiga impact"
    assert hasil.n_articles == 3


def test_model_belum_dilatih_melempar(tmp_path: Path) -> None:
    """AUDIT K-4: prediksi tanpa model harus error, bukan prior karangan."""
    from model.common.baseline import BaselineTfidfSentiment, ModelNotFittedError

    model = BaselineTfidfSentiment()
    with pytest.raises(ModelNotFittedError):
        model.predict_probs(["Gold rallies"])


@requires_model
def test_model_memuat_dan_memberi_sinyal_berbeda() -> None:
    """Model terlatih harus memberi skor berbeda untuk teks berbeda.

    Test ini menggagalkan fallback prior konstan: bila model mengembalikan
    [0.2, 0.6, 0.2] untuk semua teks, dua skor di bawah akan identik.
    """
    from model.common.baseline import BaselineTfidfSentiment

    model = BaselineTfidfSentiment.load(MODEL_PATH)
    naik = model.predict_probs(["Gold surges to record high on safe haven demand"])[0]
    turun = model.predict_probs(["Gold plunges as dollar rallies sharply"])[0]

    assert (naik.p_pos, naik.p_neu, naik.p_neg) != (turun.p_pos, turun.p_neu, turun.p_neg)
    assert naik.p_pos > naik.p_neg
    assert turun.p_neg > turun.p_pos
