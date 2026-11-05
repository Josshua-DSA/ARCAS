"""`stat_results` tidak boleh punya dua baris yang menyatakan bukti yang sama.

Latar: produksi menyimpan 80 baris untuk 3 aset, padahal hanya 68 kombinasi
uji yang berbeda. Penyebabnya dua run menulis hasil identik tanpa ada yang
membuang yang lama -- logika `save_stats` sendiri sudah mengganti per aset,
tetapi tidak ada jaminan di tingkat tabel, jadi jalur mana pun yang lupa
memanggilnya tetap bisa menumpuk.

Kunci unik memakai `COALESCE(lag, -1)`: `event_study` menyimpan `lag` NULL,
dan di SQLite setiap NULL dianggap berbeda, sehingga UNIQUE biasa akan
meloloskan baris kembar untuk semua uji tanpa lag.
"""

from datetime import date

import pytest

from backend.src.schema import StatResult
from backend.src.store.db import Database


@pytest.fixture()
def db(tmp_path):
    d = Database(tmp_path / "stat.db")
    d.init_schema()
    return d


def _stat(asset="XAU", test="ols", lag: int | None = 0, run="run01", est=0.01, n=60):
    return StatResult(
        run_id=run,
        asset_id=asset,
        test=test,
        market_metric="return",
        lag=lag,
        estimate=est,
        ci_low=-0.01,
        ci_high=0.03,
        p_value=0.5,
        p_adjusted=0.6,
        n_obs=n,
        period_start=date(2026, 7, 10),
        period_end=date(2026, 10, 28),
        params_json="{}",
        code_version="v0.5.0",
    )


def _jumlah(db, asset="XAU"):
    with db.get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM stat_results WHERE asset_id = ?;", (asset,)
        ).fetchone()[0]


def test_insert_langsung_baris_kembar_ditolak(db):
    """Bukan hanya lewat save_stats: tabel sendiri yang menolak."""
    s = _stat()
    with db.get_connection() as conn:
        conn.execute(
            """INSERT INTO stat_results (run_id, asset_id, test, market_metric, lag,
               estimate, ci_low, ci_high, p_value, p_adjusted, n_obs, period_start,
               period_end, params_json, code_version)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (s.run_id, s.asset_id, s.test, s.market_metric, s.lag, s.estimate,
             s.ci_low, s.ci_high, s.p_value, s.p_adjusted, s.n_obs,
             s.period_start.isoformat(), s.period_end.isoformat(),
             s.params_json, s.code_version),
        )
    # run_id berbeda, nilai sama -> tetap satu bukti, harus ditolak.
    lain = _stat(run="run02")
    with pytest.raises(Exception):
        with db.get_connection() as conn:
            conn.execute(
                """INSERT INTO stat_results (run_id, asset_id, test, market_metric, lag,
                   estimate, ci_low, ci_high, p_value, p_adjusted, n_obs, period_start,
                   period_end, params_json, code_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (lain.run_id, lain.asset_id, lain.test, lain.market_metric, lain.lag,
                 lain.estimate, lain.ci_low, lain.ci_high, lain.p_value,
                 lain.p_adjusted, lain.n_obs, lain.period_start.isoformat(),
                 lain.period_end.isoformat(), lain.params_json, lain.code_version),
            )
    assert _jumlah(db) == 1


def test_lag_null_tetap_terjaga(db):
    """`event_study` ber-lag NULL; UNIQUE biasa akan meloloskannya."""
    s = _stat(test="event_study", lag=None)
    db.save_stats("XAU", [s])
    db.save_stats("XAU", [_stat(test="event_study", lag=None, run="run02")])
    assert _jumlah(db) == 1


def test_lag_berbeda_tetap_dua_baris(db):
    """Lag berbeda adalah uji berbeda; kunci unik tidak boleh menelannya."""
    db.save_stats("XAU", [_stat(lag=1, est=0.02), _stat(lag=2, est=0.02)])
    assert _jumlah(db) == 2


def test_aset_berbeda_tetap_dua_baris(db):
    db.save_stats("XAU", [_stat(asset="XAU")])
    db.save_stats("SPX", [_stat(asset="SPX")])
    assert _jumlah(db, "XAU") == 1
    assert _jumlah(db, "SPX") == 1


def test_jenis_uji_beda_tetap_dua_baris(db):
    db.save_stats("XAU", [_stat(test="ols"), _stat(test="event_study", lag=None)])
    assert _jumlah(db) == 2


def test_migrasi_membuang_baris_kembar_lama(db):
    """DB produksi sudah berisi 12 baris kembar; migrasi harus membersihkannya."""
    d = Database(db.db_path)
    # Bangun kondisi lama: tanpa kunci unik, lalu isi kembar.
    with d.get_connection() as conn:
        conn.execute("DROP INDEX IF EXISTS ux_stat_results_bukti;")
        s = _stat()
        for run in ("run01", "run02", "run03"):
            conn.execute(
                """INSERT INTO stat_results (run_id, asset_id, test, market_metric, lag,
                   estimate, ci_low, ci_high, p_value, p_adjusted, n_obs, period_start,
                   period_end, params_json, code_version)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run, s.asset_id, s.test, s.market_metric, s.lag, s.estimate,
                 s.ci_low, s.ci_high, s.p_value, s.p_adjusted, s.n_obs,
                 s.period_start.isoformat(), s.period_end.isoformat(),
                 s.params_json, s.code_version),
            )
        assert conn.execute("SELECT COUNT(*) FROM stat_results;").fetchone()[0] == 3

    d.init_schema()  # migrasi berjalan

    assert _jumlah(db) == 1
    with d.get_connection() as conn:
        idx = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='ux_stat_results_bukti';"
        ).fetchone()
    assert idx is not None, "indeks unik tidak terpasang setelah migrasi"


def test_migrasi_idempoten(db):
    """init_schema dipanggil setiap start; menjalankannya dua kali harus aman."""
    db.save_stats("XAU", [_stat(), _stat(lag=1, est=0.02)])
    db.init_schema()
    db.init_schema()
    assert _jumlah(db) == 2
