"""stat_results harus diganti, bukan ditumpuk, setiap pipeline dijalankan ulang.

Konteks: pipeline dipanggil ulang setiap server hidup (catch-up startup). Dulu
`save_stat` memakai INSERT biasa, sehingga tiap restart menambah satu batch
duplikat — 35 baris menjadi 70, 105, dan seterusnya, dan panel Research Lab
menampilkan uji yang sama berulang kali.
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


def _stat(asset="XAU", test="ols", lag=0, run="run01", est=0.01):
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
        n_obs=60,
        period_start=date(2026, 7, 10),
        period_end=date(2026, 10, 28),
        params_json="{}",
        code_version="v0.5.0",
    )


def test_jalan_ulang_tidak_menggandakan(db):
    """Batch kedua menggantikan batch pertama, bukan menumpuk di sampingnya."""
    batch = [_stat(), _stat(test="granger", lag=1)]

    db.save_stats("XAU", batch)
    db.save_stats("XAU", batch)

    assert len(db.query_stats("XAU")) == 2


def test_hasil_baru_benar_benar_menggantikan_yang_lama(db):
    """Bukan hanya jumlahnya sama — nilainya harus dari run terakhir."""
    db.save_stats("XAU", [_stat(run="lama", est=0.01)])
    db.save_stats("XAU", [_stat(run="baru", est=0.99)])

    rows = db.query_stats("XAU")
    assert len(rows) == 1
    assert rows[0].run_id == "baru"
    assert rows[0].estimate == pytest.approx(0.99)


def test_aset_lain_tidak_ikut_terhapus(db):
    """Menghapus per aset, supaya aset yang gagal dihitung tetap punya hasil."""
    db.save_stats("XAU", [_stat(asset="XAU")])
    db.save_stats("SPX", [_stat(asset="SPX")])
    db.save_stats("XAU", [_stat(asset="XAU", run="kedua")])

    assert len(db.query_stats("XAU")) == 1
    assert len(db.query_stats("SPX")) == 1
    assert db.query_stats("SPX")[0].run_id == "run01"


def test_mengembalikan_jumlah_baris_yang_ditulis(db):
    assert db.save_stats("XAU", [_stat(), _stat(test="granger", lag=1)]) == 2
    assert db.save_stats("XAU", []) == 0
