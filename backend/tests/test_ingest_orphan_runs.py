"""Run ingest yatim harus ditutup saat startup.

Proses yang mati antara `claim_ingest_slot` dan `finish_ingest_run` meninggalkan
baris berstatus 'running' dengan `finished_at` NULL. Baris itu tidak pernah
ditutup siapa pun: `last_ingest_run` melewatkannya, dan slot terjadwal bisa
menganggap dirinya masih diklaim selama `started_at` belum lewat batas klaim.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from backend.src.store.db import Database


def _db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "uji.db")
    db.init_schema()
    return db


def _sisip(db: Database, mulai: datetime, status: str = "running") -> int:
    with db.get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO ingest_runs (trigger, status, started_at, scheduled_for)
            VALUES ('startup_catchup', ?, ?, ?);
            """,
            (status, mulai.isoformat(), mulai.isoformat()),
        )
        return int(cur.lastrowid or 0)


def _baris(db: Database, run_id: int) -> sqlite3.Row:
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT * FROM ingest_runs WHERE run_id = ?;", (run_id,)
        ).fetchone()


def test_run_yatim_ditutup_saat_startup(tmp_path: Path) -> None:
    db = _db(tmp_path)
    lama = datetime.now() - timedelta(days=9)
    run_id = _sisip(db, lama)

    jumlah = db.close_orphan_ingest_runs()
    assert jumlah == 1

    r = _baris(db, run_id)
    assert r["status"] == "failed"
    assert r["finished_at"] is not None
    assert r["detail"] and "yatim" in r["detail"]


def test_run_yang_masih_baru_tidak_disentuh(tmp_path: Path) -> None:
    """Proses yang benar-benar masih berjalan tidak boleh dicap gagal."""
    db = _db(tmp_path)
    baru = datetime.now() - timedelta(seconds=30)
    run_id = _sisip(db, baru)

    assert db.close_orphan_ingest_runs() == 0
    assert _baris(db, run_id)["status"] == "running"


def test_run_yang_sudah_selesai_tidak_disentuh(tmp_path: Path) -> None:
    db = _db(tmp_path)
    lama = datetime.now() - timedelta(days=9)
    run_id = _sisip(db, lama, status="ok")

    assert db.close_orphan_ingest_runs() == 0
    r = _baris(db, run_id)
    assert r["status"] == "ok"
    assert r["finished_at"] is None  # tidak diubah


def test_idempoten(tmp_path: Path) -> None:
    db = _db(tmp_path)
    _sisip(db, datetime.now() - timedelta(days=9))
    assert db.close_orphan_ingest_runs() == 1
    assert db.close_orphan_ingest_runs() == 0


def test_run_yatim_tidak_jadi_cap_waktu_gui(tmp_path: Path) -> None:
    """Run yatim punya finished_at paling baru; ia tidak boleh jadi cap waktu.

    Kalau ikut terpilih, GUI menyatakan data segar padahal yang terakhir
    berjalan justru gagal dan tidak menarik apa pun.
    """
    db = _db(tmp_path)
    _sisip(db, datetime.now() - timedelta(days=9))
    db.close_orphan_ingest_runs()
    assert db.last_ingest_run() is None


def test_cap_waktu_memakai_run_sukses_terakhir(tmp_path: Path) -> None:
    db = _db(tmp_path)
    lama = _sisip(db, datetime.now() - timedelta(days=9), status="ok")
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE ingest_runs SET finished_at = ? WHERE run_id = ?;",
            ((datetime.now() - timedelta(days=9)).isoformat(), lama),
        )
    _sisip(db, datetime.now() - timedelta(days=8))
    db.close_orphan_ingest_runs()

    terakhir = db.last_ingest_run()
    assert terakhir is not None
    assert terakhir["run_id"] == lama
    assert terakhir["status"] == "ok"
