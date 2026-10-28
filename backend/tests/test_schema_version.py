"""Uji P3-5: versi skema, migrasi per-tabel, seed idempoten.

Masalah yang ditutup: `CREATE TABLE IF NOT EXISTS` tidak menyentuh tabel yang
sudah ada, dan `_migrate` hanya menangani tabel `impacts`. Kolom baru pada tabel
lain tidak pernah masuk ke DB lama, sehingga query gagal saat runtime -- atau
berjalan diam-diam dengan data tidak lengkap. Tidak ada `user_version` maupun
tabel versi, jadi DB lama dan baru tidak bisa dibedakan.
"""
from __future__ import annotations

import sqlite3

from backend.src.store.db import Database


def _db_lama(path) -> Database:
    """Bikin DB 'zaman dulu': tabel sudah ADA tapi belum punya kolom susulan.

    Penting: tabel harus dibuat dengan bentuk LAMA, bukan dibiarkan kosong.
    `CREATE TABLE IF NOT EXISTS` tidak menyentuh tabel yang sudah ada, jadi
    hanya bentuk lama seperti ini yang benar-benar menguji jalur migrasi.
    Versi lama tes ini hanya membuat `impacts`, sehingga tabel lain dibuat
    lengkap oleh DDL dan migrasi tak pernah dieksekusi.
    """
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE impacts (
          impact_id INTEGER PRIMARY KEY AUTOINCREMENT,
          article_id TEXT NOT NULL, asset_id TEXT NOT NULL,
          direction TEXT NOT NULL, confidence REAL NOT NULL,
          created_at TIMESTAMP NOT NULL
        );
        CREATE TABLE raw_articles (
          raw_id INTEGER PRIMARY KEY AUTOINCREMENT,
          source TEXT NOT NULL, title TEXT NOT NULL,
          fetched_at TIMESTAMP NOT NULL
        );
        CREATE TABLE articles (
          article_id TEXT PRIMARY KEY, source TEXT NOT NULL,
          title TEXT NOT NULL, language TEXT NOT NULL,
          fetched_at TIMESTAMP NOT NULL
        );
        CREATE TABLE ingest_runs (
          run_id INTEGER PRIMARY KEY AUTOINCREMENT,
          trigger TEXT NOT NULL, status TEXT NOT NULL,
          started_at TIMESTAMP NOT NULL
        );
        CREATE TABLE source_health (
          source TEXT NOT NULL, checked_at TIMESTAMP NOT NULL
        );
        CREATE TABLE sim_runs (
          run_id INTEGER PRIMARY KEY AUTOINCREMENT,
          created_at TIMESTAMP NOT NULL, text_hash TEXT NOT NULL,
          text TEXT NOT NULL, input_kind TEXT NOT NULL,
          target TEXT NOT NULL, tone TEXT NOT NULL, score REAL NOT NULL,
          confidence REAL NOT NULL, confidence_raw REAL NOT NULL,
          direction TEXT NOT NULL, model_version TEXT NOT NULL
        );
        INSERT INTO impacts (article_id, asset_id, direction, confidence,
                             created_at)
          VALUES ('a1','XAU','bullish',0.9,'2026-01-01');
        INSERT INTO raw_articles (source, title, fetched_at)
          VALUES ('x','berita lama','2026-01-01');
        INSERT INTO sim_runs (created_at, text_hash, text, input_kind, target,
                              tone, score, confidence, confidence_raw,
                              direction, model_version)
          VALUES ('2026-01-01','h','teks','berita','XAU','positive',0.9,0.8,0.8,
                  'bullish','v1');
        """
    )
    conn.commit()
    conn.close()
    return Database(path)


# -- versi skema -----------------------------------------------------------


def test_db_baru_mendapat_versi_terbaru(temp_db):
    temp_db.init_schema()
    with temp_db.get_connection() as conn:
        assert temp_db.versi_skema(conn) == Database.SCHEMA_VERSION


def test_db_lama_tanpa_versi_dilaporkan_nol(tmp_path):
    """DB yang belum pernah dimigrasi harus terbaca 0, bukan versi kode.

    Ini regresi untuk bug nyata: deteksi lama hanya memeriksa tabel `impacts`,
    sehingga DB setengah jadi dinilai "sudah v1" padahal `articles` belum ada.
    """
    db = _db_lama(tmp_path / "lama.db")
    with db.get_connection() as conn:
        assert db.versi_skema(conn) == 0


def test_versi_naik_setelah_migrasi(tmp_path):
    db = _db_lama(tmp_path / "lama.db")
    with db.get_connection() as conn:
        assert db.versi_skema(conn) == 0

    db.init_schema()

    with db.get_connection() as conn:
        assert db.versi_skema(conn) == Database.SCHEMA_VERSION


# -- migrasi kolom per-tabel ----------------------------------------------


def test_migrasi_melengkapi_semua_tabel_bukan_hanya_impacts(tmp_path):
    """Inti P3-5: kolom di tabel LAIN juga harus ikut ditambahkan."""
    db = _db_lama(tmp_path / "lama.db")
    db.init_schema()

    with db.get_connection() as conn:
        assert db.skema_tidak_lengkap(conn) == [], "masih ada kolom yang hilang"
        # Buktikan kolom yang dulu tidak pernah dimigrasi kini ada.
        kolom_raw = {r["name"] for r in conn.execute("PRAGMA table_info(raw_articles);")}
        assert {"query_target", "vendor_sentiment", "payload_json"} <= kolom_raw


def test_migrasi_tidak_menghilangkan_data_lama(tmp_path):
    db = _db_lama(tmp_path / "lama.db")
    db.init_schema()

    with db.get_connection() as conn:
        baris = conn.execute("SELECT direction, confidence FROM impacts").fetchone()
        assert tuple(baris) == ("bullish", 0.9)


def test_migrasi_idempoten(temp_db):
    temp_db.init_schema()
    temp_db.init_schema()
    temp_db.init_schema()

    with temp_db.get_connection() as conn:
        assert temp_db.skema_tidak_lengkap(conn) == []
        assert temp_db.versi_skema(conn) == Database.SCHEMA_VERSION


def test_kolom_wajib_benar_benar_ada_di_ddl():
    """Jaga agar peta migrasi tidak memuat kolom yang tidak pernah ada.

    Tanpa tes ini, salah ketik nama kolom membuat migrasi menambah kolom asing
    yang tidak dipakai kode mana pun -- dan `check-schema` tetap bilang "lengkap".
    """
    from backend.src.store.db import DDL_SCHEMA

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(DDL_SCHEMA)
    for tabel, kolom in Database.KOLOM_WAJIB.items():
        ada = {r["name"] for r in conn.execute(f"PRAGMA table_info({tabel});")}
        assert ada, f"tabel {tabel} tidak ada di DDL_SCHEMA"
        for nama in kolom:
            assert nama in ada, f"{tabel}.{nama} tidak ada di DDL_SCHEMA"
    conn.close()


# -- seed yang tidak menimpa ---------------------------------------------


def test_seed_mengisi_universe_terkunci(temp_db):
    temp_db.init_schema()
    with temp_db.get_connection() as conn:
        ids = {r["asset_id"] for r in conn.execute("SELECT asset_id FROM asset_master;")}
    assert {"XAU", "RATE_UST", "SPX"} <= ids


def test_seed_tidak_menimpa_perubahan_pengguna(temp_db):
    """`ON CONFLICT DO NOTHING`: data yang sudah ada tidak boleh ditimpa."""
    temp_db.init_schema()
    with temp_db.get_connection() as conn:
        conn.execute("UPDATE asset_master SET name='Gold Ubahan' WHERE asset_id='XAU';")

    temp_db.init_schema()  # dijalankan ulang

    with temp_db.get_connection() as conn:
        nama = conn.execute(
            "SELECT name FROM asset_master WHERE asset_id='XAU';"
        ).fetchone()[0]
        jumlah = conn.execute("SELECT COUNT(*) FROM asset_master;").fetchone()[0]
    assert nama == "Gold Ubahan", "seed menimpa data pengguna"
    assert jumlah == 3, "seed menggandakan baris"


def test_seed_mengisi_kolom_not_null(tmp_path):
    """`price_ticker` NOT NULL di DDL; seed tidak boleh mengirim None."""
    db = _db_lama(tmp_path / "lama.db")
    db.init_schema()
    with db.get_connection() as conn:
        kosong = conn.execute(
            "SELECT COUNT(*) FROM asset_master WHERE price_ticker IS NULL;"
        ).fetchone()[0]
    assert kosong == 0


# -- deteksi tanpa mengubah ----------------------------------------------


def test_skema_tidak_lengkap_tidak_mengubah_apa_pun(tmp_path):
    db = _db_lama(tmp_path / "lama.db")
    with db.get_connection() as conn:
        before = db.versi_skema(conn)
        hilang = db.skema_tidak_lengkap(conn)
        after = db.versi_skema(conn)
    assert hilang, "DB lama seharusnya dilaporkan tidak lengkap"
    assert before == after == 0, "pemeriksaan tidak boleh memigrasi diam-diam"
