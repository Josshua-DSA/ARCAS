"""Tes untuk tiga celah integrasi GUI/backend yang sempat lolos.

Ketiganya punya gejala yang sama: tampak "tidak ada data" padahal mesinnya
sehat. Karena itu tes di sini mengunci *penjelasan*, bukan hanya nilai:

1. `fi pipeline` wajib mengisi `stat_results`. Sebelumnya langkah statistik
   hanya ada di subperintah `fi stats`, sehingga pipeline bisa sukses penuh
   sementara panel uji di Research Lab kosong.
2. `/api/stats/{target}?max_lag=N` tidak boleh mengembalikan [] tanpa alasan;
   bila data kurang, sebutkan berapa hari berpasangan yang ada.
3. GUI statis harus disajikan proses yang sama tanpa menutupi route /api.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from backend.src.serve.app import create_app
from backend.src.stats.engine import StatEngine
from backend.src.store.db import Database


@pytest.fixture()
def klien(tmp_path, monkeypatch):
    """Klien API dengan DB kosong dan scheduler/warm-up dimatikan."""
    monkeypatch.setenv("ARCAS_DISABLE_SCHEDULER", "1")
    monkeypatch.setenv("ARCAS_WARMUP_TIMEOUT", "0")
    db_path = tmp_path / "api.db"
    db = Database(db_path)
    db.init_schema()
    app = create_app(db_path=db_path)
    with TestClient(app) as c:
        yield c, db


# ---------------------------------------------------------------- celah #1


def test_pipeline_mengisi_stat_results(tmp_path):
    """`Pipeline.run` harus menulis stat_results, bukan hanya daily_sentiment.

    Dibangun dari data sintetis yang sengaja punya >= 5 hari berpasangan
    supaya OLS/Granger/CAR benar-benar bisa dihitung. Bila langkah statistik
    hilang lagi dari alur, tabel kembali kosong dan tes ini gagal.
    """
    from datetime import date, timedelta

    from backend.src.pipeline.runner import Pipeline
    from backend.src.schema import DailySentiment, PriceRecord

    db_path = tmp_path / "pipe.db"
    db = Database(db_path)
    db.init_schema()
    Pipeline(db_path=db_path).seed_universe()

    mulai = date(2026, 1, 1)
    for i in range(20):
        tgl = mulai + timedelta(days=i)
        db.save_daily_sentiment(
            DailySentiment(
                asset_id="XAU",
                date=tgl,
                # Melewati spike_threshold (0.5) supaya CAR punya event;
                # tanpa lonjakan, event_study memang (benar) mengembalikan [].
                score_mean=0.9 if i % 4 == 0 else 0.05 * ((i % 5) - 2),
                n_articles=3,
                n_sources=1,
                has_news=True,
            )
        )
        db.save_price(
            PriceRecord(
                asset_id="XAU",
                date=tgl,
                open=1999.0,
                high=2005.0,
                low=1995.0,
                close=2000.0 + (i % 7) * 3.0,
                adj_close=2000.0 + (i % 7) * 3.0,
                volume=1000.0,
            )
        )

    assert db.query_stats("XAU") == [], "prasyarat: tabel harus kosong sebelum run"

    pipe = Pipeline(db_path=db_path)
    stats = pipe.compute_stats()

    assert stats.baris_statistik > 0, "compute_stats tidak menulis baris apa pun"
    tersimpan = db.query_stats("XAU")
    assert tersimpan, "stat_results tetap kosong setelah compute_stats"
    # CAR ikut, karena itu yang dipakai panel Research Lab.
    assert any(r.test == "event_study" for r in tersimpan)


def test_run_memanggil_langkah_statistik(tmp_path, monkeypatch):
    """`run()` harus menyertakan compute_stats, bukan hanya aggregate."""
    from backend.src.pipeline import runner as mod

    dipanggil: list[str] = []

    def fake_compute(self, dry_run=False, stats=None):
        dipanggil.append("compute_stats")
        return stats or mod.PipelineStats()

    monkeypatch.setattr(mod.Pipeline, "compute_stats", fake_compute)
    monkeypatch.setattr(mod.Pipeline, "normalize_raw", lambda self, **kw: ([], mod.PipelineStats()))
    monkeypatch.setattr(
        mod.Pipeline, "score_and_route", lambda self, a, **kw: ([], mod.PipelineStats())
    )
    monkeypatch.setattr(mod.Pipeline, "aggregate", lambda self, i, a, **kw: mod.PipelineStats())
    monkeypatch.setattr(mod.Pipeline, "seed_universe", lambda self: None)

    mod.Pipeline(db_path=tmp_path / "r.db").run(seed=False)
    assert dipanggil == ["compute_stats"], "run() tidak memanggil langkah statistik"


# ---------------------------------------------------------------- celah #2


def test_max_lag_kosong_menyebut_alasan(klien):
    """Data kurang harus 409 dengan angka, bukan [] yang membingungkan."""
    klien_http, db = klien

    resp = klien_http.get("/api/stats/XAU", params={"max_lag": 5})

    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail["kode"] == "data_belum_cukup"
    assert detail["hari_berpasangan"] == 0
    assert detail["hari_minimum"] == 5
    assert "XAU" in detail["pesan"]


def test_hitung_hari_berpasangan_hanya_tanggal_irisan():
    """Hanya tanggal yang punya sentimen DAN harga yang dihitung."""
    daily = [{"date": "2026-01-01"}, {"date": "2026-01-02"}, {"date": "2026-01-03"}]
    prices = [{"date": "2026-01-02"}, {"date": "2026-01-03"}, {"date": "2026-01-04"}]
    assert StatEngine.hitung_hari_berpasangan(daily, prices) == 2


def test_max_lag_tetap_jalan_saat_data_cukup(klien):
    """Perbaikan tidak boleh merusak jalur sukses."""
    from datetime import date, timedelta

    klien_http, db = klien
    from backend.src.schema import DailySentiment, PriceRecord

    mulai = date(2026, 1, 1)
    for i in range(30):
        tgl = mulai + timedelta(days=i)
        db.save_daily_sentiment(
            DailySentiment(
                asset_id="XAU",
                date=tgl,
                score_mean=0.1 * ((i % 5) - 2),
                n_articles=3,
                n_sources=1,
                has_news=True,
            )
        )
        db.save_price(
            PriceRecord(
                asset_id="XAU",
                date=tgl,
                open=1999.0,
                high=2005.0,
                low=1995.0,
                close=2000.0 + (i % 7) * 3.0,
                adj_close=2000.0 + (i % 7) * 3.0,
                volume=1000.0,
            )
        )

    resp = klien_http.get("/api/stats/XAU", params={"max_lag": 2})
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) > 0


# ---------------------------------------------------------------- celah #3


def test_gui_disajikan_dan_api_tidak_tertutup(klien):
    """Mount "/" tidak boleh menelan route /api."""
    klien_http, _ = klien

    assert klien_http.get("/health").status_code == 200
    assert klien_http.get("/api/meta").status_code == 200

    halaman = klien_http.get("/research.html")
    assert halaman.status_code == 200, "GUI tidak disajikan backend"
    assert "text/html" in halaman.headers["content-type"]

    akar = klien_http.get("/")
    assert akar.status_code == 200, "index.html tidak tersaji di akar"
    assert "text/html" in akar.headers["content-type"]


def test_gui_bisa_dimatikan(tmp_path, monkeypatch):
    """ARCAS_SERVE_GUI=0 harus benar-benar mematikan mount GUI."""
    monkeypatch.setenv("ARCAS_DISABLE_SCHEDULER", "1")
    monkeypatch.setenv("ARCAS_WARMUP_TIMEOUT", "0")
    monkeypatch.setenv("ARCAS_SERVE_GUI", "0")

    db_path = tmp_path / "nogui.db"
    Database(db_path).init_schema()
    app = create_app(db_path=db_path)

    with TestClient(app) as c:
        assert c.get("/api/meta").status_code == 200
        assert c.get("/research.html").status_code == 404


def test_mount_gui_tidak_bentrok_dengan_api():
    """Setiap route /api harus terdaftar sebelum mount "/" dipasang."""
    import inspect

    from backend.src.serve import app as mod

    sumber = inspect.getsource(mod.create_app)
    posisi_mount = sumber.find('app.mount("/"')
    posisi_return = sumber.rfind("return app")
    assert posisi_mount != -1, "mount GUI tidak ditemukan"
    assert posisi_mount < posisi_return, "mount harus dipasang tepat sebelum return"
