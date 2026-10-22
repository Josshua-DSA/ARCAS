"""Tests for T-3: riwayat kesehatan sumber & alert (FR-18).

Yang diuji bukan sekadar "tabel bisa diisi", tetapi perilaku yang membuat
alert berguna: tidak berbunyi karena gangguan sesaat, berhenti saat pulih,
dan tidak salah menghitung `no_key` sebagai sumber mati.
"""

from datetime import datetime, timedelta

import pytest

from backend.src.store.db import Database


@pytest.fixture()
def db(tmp_path):
    d = Database(tmp_path / "test.db")
    d.init_schema()
    return d


def test_table_exists_after_init(db):
    with db.get_connection() as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='source_health';"
        ).fetchone()
    assert row is not None


def test_success_resets_streak(db):
    assert db.save_source_health("finnhub", "error", "putus") == 1
    assert db.save_source_health("finnhub", "error", "putus") == 2
    assert db.save_source_health("finnhub", "ok", "sehat", usable=True) == 0


def test_alert_only_after_threshold_consecutive_failures(db):
    """Satu-dua kegagalan belum boleh memicu alert."""
    db.save_source_health("marketaux", "error", "putus")
    assert db.sources_needing_alert(3) == []
    db.save_source_health("marketaux", "error", "putus")
    assert db.sources_needing_alert(3) == []
    db.save_source_health("marketaux", "error", "putus")
    alerts = db.sources_needing_alert(3)
    assert [a["source"] for a in alerts] == ["marketaux"]


def test_alert_clears_after_recovery(db):
    """Setelah sumber pulih, alert harus berhenti -- bukan menyala selamanya."""
    for _ in range(3):
        db.save_source_health("finnhub", "error", "putus")
    assert db.sources_needing_alert(3), "harus ada alert saat masih gagal"

    db.save_source_health("finnhub", "ok", "sehat", usable=True)
    assert db.sources_needing_alert(3) == [], "alert harus padam setelah pulih"


def test_no_key_is_not_a_failure(db):
    """`no_key` adalah pilihan konfigurasi, bukan sumber yang mati."""
    for _ in range(5):
        db.save_source_health("eulerpool", "no_key", "EULERPOOL_API_KEY tidak diset")
    assert db.sources_needing_alert(1) == []


@pytest.mark.parametrize("status", ["unauthorized", "rate_limited", "error"])
def test_failure_statuses_counted(db, status):
    for _ in range(3):
        db.save_source_health("x", status, "gagal")
    assert db.sources_needing_alert(3)


def test_latest_returns_exactly_one_row_per_source(db):
    """Pemeriksaan dalam detik yang sama tidak boleh menghasilkan baris ganda.

    `checked_at` beresolusi detik; tanpa pemecah seri, MAX(checked_at) akan
    mencocokkan banyak baris dan laporan menampilkan sumber yang sama 4x.
    """
    same_instant = datetime(2026, 1, 1, 12, 0, 0)
    for _ in range(4):
        db.save_source_health("finnhub", "error", "x", checked_at=same_instant)

    latest = db.latest_source_health()
    assert len(latest) == 1
    assert latest[0]["source"] == "finnhub"


def test_latest_picks_most_recent_per_source(db):
    t0 = datetime(2026, 1, 1, 12, 0, 0)
    db.save_source_health("a", "error", "lama", checked_at=t0)
    db.save_source_health("a", "ok", "baru", usable=True, checked_at=t0 + timedelta(hours=1))
    db.save_source_health("b", "ok", "satu-satunya", usable=True, checked_at=t0)

    latest = {r["source"]: r for r in db.latest_source_health()}
    assert latest["a"]["status"] == "ok"
    assert latest["b"]["status"] == "ok"


def test_is_failure_flag_persisted(db):
    db.save_source_health("a", "rate_limited", "429")
    db.save_source_health("b", "ok", "sehat", usable=True)

    with db.get_connection() as conn:
        rows = {
            r["source"]: r["is_failure"]
            for r in conn.execute("SELECT source, is_failure FROM source_health;")
        }
    assert rows["a"] == 1
    assert rows["b"] == 0


def test_usable_flag_persisted(db):
    db.save_source_health("a", "ok", "sehat", usable=True)
    db.save_source_health("b", "empty", "nol hasil", usable=False)

    with db.get_connection() as conn:
        rows = {
            r["source"]: r["usable"]
            for r in conn.execute("SELECT source, usable FROM source_health;")
        }
    assert rows["a"] == 1
    assert rows["b"] == 0


def test_long_detail_is_truncated(db):
    """Detail sangat panjang tidak boleh menggembungkan tabel tanpa batas."""
    db.save_source_health("a", "error", "x" * 5000)
    with db.get_connection() as conn:
        detail = conn.execute("SELECT detail FROM source_health;").fetchone()["detail"]
    assert len(detail) <= 500


def test_multiple_sources_alerted_independently(db):
    for _ in range(3):
        db.save_source_health("a", "error", "x")
    db.save_source_health("b", "error", "x")

    assert [x["source"] for x in db.sources_needing_alert(3)] == ["a"]
