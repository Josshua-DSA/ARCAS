"""S-4: test yang menyentuh jalur nyata, bukan hanya komponen terpisah.

AUDIT K-1 lolos justru karena setiap komponen diuji sendiri-sendiri dengan
`tmpdir`: `ArticleCleaner` diuji, `TargetRouter` diuji, `DailyAggregator`
diuji — tetapi tidak ada yang menguji bahwa keluaran satu tahap benar-benar
masuk ke tahap berikutnya.

Test ini menjalankan CLI bertahap (`clean` -> `score` -> `aggregate`) pada satu
database, dengan model nyata, lalu memeriksa bahwa tiap tahap menambah baris
yang dibuat oleh tahap sebelumnya. Bila salah satu sambungan putus, jumlahnya
akan nol dan test gagal.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from backend.src.cli import main
from backend.src.store.db import Database

MODEL_PATH = Path("model/common/baseline_tfidf.joblib")
requires_model = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason="latih dulu: python -m model.common.train_baseline",
)

BERITA = [
    ("Gold rallies as Fed signals rate cuts ahead", "rss:kitco"),
    ("Gold falls sharply as dollar strengthens", "finnhub:Reuters"),
    ("S&P 500 closes at record high on tech rally", "finnhub:CNBC"),
]


def _count(db_path: str, table: str) -> int:
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


@pytest.fixture()
def seeded_db(tmp_path: Path) -> str:
    """Database dengan skema lengkap dan raw_articles siap olah."""
    path = str(tmp_path / "jalur.db")
    db = Database(path)
    db.init_schema()
    db.seed_asset_master()

    now = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=1)
    with db.get_connection() as conn:
        for judul, sumber in BERITA:
            conn.execute(
                """
                INSERT INTO raw_articles (
                    source, url, title, body, published_at, fetched_at,
                    query_target, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    sumber,
                    f"https://contoh.test/{abs(hash(judul))}",
                    judul,
                    judul,
                    now.isoformat(),
                    now.isoformat(),
                    "XAU",
                    "{}",
                ),
            )
    return path


# ==========================================================
# Sambungan antar tahap
# ==========================================================


@requires_model
def test_clean_membuat_articles(seeded_db, capsys):
    """Tahap 1: raw_articles -> articles."""
    assert _count(seeded_db, "articles") == 0

    assert main(["--db", seeded_db, "clean"]) == 0

    assert _count(seeded_db, "articles") == len(BERITA), (
        "clean tidak menulis articles — sambungan raw_articles -> articles putus"
    )


@requires_model
def test_score_membaca_tabel_articles_bukan_raw(seeded_db, capsys):
    """Tahap 2 harus memakai hasil `clean`, bukan mengolah ulang `raw_articles`.

    S-4: `cmd_score` dulu memanggil `normalize_raw(dry_run=True)`, jadi `clean`
    praktis opsional dan `score` tanpa `clean` gagal dengan
    `FOREIGN KEY constraint failed`. Test ini membedakan kedua sumber:
    `raw_articles` dikosongkan setelah `clean`, sehingga hanya pembacaan dari
    tabel `articles` yang bisa menghasilkan impact.
    """
    assert main(["--db", seeded_db, "clean"]) == 0
    assert _count(seeded_db, "articles") == len(BERITA)

    # Hapus sumber mentah: bila `score` masih membaca raw_articles, ia kosong.
    conn = sqlite3.connect(seeded_db)
    try:
        conn.execute("DELETE FROM raw_articles;")
        conn.commit()
    finally:
        conn.close()

    assert main(["--db", seeded_db, "score"]) == 0

    assert _count(seeded_db, "sentiments") > 0, "score tidak menulis sentimen"
    assert _count(seeded_db, "impacts") > 0, (
        "score tidak menghasilkan impact padahal `articles` berisi — "
        "tahap ini masih membaca raw_articles, bukan hasil `clean`"
    )


@requires_model
def test_score_tanpa_clean_memberi_pesan_jelas(seeded_db, capsys):
    """`score` sebelum `clean` harus menolak dengan pesan, bukan crash SQLite."""
    kode = main(["--db", seeded_db, "score"])
    out = capsys.readouterr().out

    assert kode == 1, "harus gagal terkontrol, bukan sukses palsu"
    assert "clean" in out, "pesan harus menyebut perintah yang harus dijalankan"
    assert "FOREIGN KEY" not in out


@requires_model
def test_aggregate_memakai_impacts_dari_score(seeded_db, capsys):
    """Tahap 3: impacts -> daily_sentiment."""
    assert main(["--db", seeded_db, "clean"]) == 0
    assert main(["--db", seeded_db, "score"]) == 0
    assert main(["--db", seeded_db, "aggregate"]) == 0

    assert _count(seeded_db, "daily_sentiment") > 0, (
        "aggregate tidak menulis daily_sentiment — sambungan impacts -> harian putus"
    )


@requires_model
def test_seluruh_jalur_berurutan(seeded_db):
    """Ketiga tahap berurutan menghasilkan data di semua tabel berita."""
    for tahap in ("clean", "score", "aggregate"):
        assert main(["--db", seeded_db, tahap]) == 0

    for tabel in ("articles", "sentiments", "impacts", "daily_sentiment"):
        assert _count(seeded_db, tabel) > 0, f"{tabel} kosong setelah pipeline penuh"


# ==========================================================
# Atribut yang harus selamat melewati seluruh jalur
# ==========================================================


@requires_model
def test_horizon_sampai_ke_database(seeded_db):
    """S-5 lewat jalur nyata: horizon harus terisi, bukan NULL."""
    for tahap in ("clean", "score", "aggregate"):
        assert main(["--db", seeded_db, tahap]) == 0

    conn = sqlite3.connect(seeded_db)
    try:
        total = conn.execute("SELECT COUNT(*) FROM impacts").fetchone()[0]
        terisi = conn.execute(
            "SELECT COUNT(*) FROM impacts WHERE news_horizon IS NOT NULL"
        ).fetchone()[0]
    finally:
        conn.close()

    assert total > 0
    assert terisi == total, f"hanya {terisi}/{total} impact punya news_horizon"


@requires_model
def test_daily_sentiment_punya_hari_dan_target(seeded_db):
    """Baris harian harus menunjuk aset yang benar, bukan placeholder."""
    for tahap in ("clean", "score", "aggregate"):
        assert main(["--db", seeded_db, tahap]) == 0

    conn = sqlite3.connect(seeded_db)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT asset_id, date, n_articles FROM daily_sentiment"
        ).fetchall()
    finally:
        conn.close()

    assert rows
    for r in rows:
        assert r["asset_id"], "asset_id kosong pada daily_sentiment"
        assert r["date"], "tanggal kosong pada daily_sentiment"
        assert r["n_articles"] >= 1


@requires_model
def test_pipeline_idempoten_lewat_cli(seeded_db):
    """Menjalankan ulang tidak menggandakan baris."""
    for tahap in ("clean", "score", "aggregate"):
        assert main(["--db", seeded_db, tahap]) == 0
    sekali = {
        t: _count(seeded_db, t)
        for t in ("articles", "sentiments", "impacts", "daily_sentiment")
    }

    for tahap in ("clean", "score", "aggregate"):
        assert main(["--db", seeded_db, tahap]) == 0
    dua_kali = {
        t: _count(seeded_db, t)
        for t in ("articles", "sentiments", "impacts", "daily_sentiment")
    }

    assert sekali == dua_kali, f"pipeline menggandakan baris: {sekali} -> {dua_kali}"


@requires_model
def test_dry_run_tidak_mengubah_database(seeded_db):
    """`--dry-run` tidak boleh menulis apa pun di tahap mana pun.

    `score --dry-run` butuh `articles` sudah terisi (hasil `clean` sungguhan),
    karena kini tahap itu membaca tabel `articles`, bukan `raw_articles`.
    """
    assert main(["--db", seeded_db, "clean"]) == 0
    sebelum = {t: _count(seeded_db, t) for t in ("articles", "sentiments", "impacts")}

    for tahap in ("score", "aggregate"):
        assert main(["--db", seeded_db, tahap, "--dry-run"]) == 0

    sesudah = {t: _count(seeded_db, t) for t in ("articles", "sentiments", "impacts")}
    assert sebelum == sesudah, f"dry-run menulis ke DB: {sebelum} -> {sesudah}"
