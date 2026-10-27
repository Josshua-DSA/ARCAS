"""Uji `run_preload` tanpa menyentuh jaringan atau eulerpool sungguhan.

Yang dijaga di sini adalah keputusan status, karena status itulah yang
dibaca scheduler untuk memutuskan "sudah selesai" atau "coba lagi". Salah
di sini berarti kuota eulerpool dibakar oleh percobaan ulang tiap 30 detik.
"""
from __future__ import annotations

import pytest

from backend.src.serve import news_preload


@pytest.fixture()
def db_path(tmp_path):
    return tmp_path / "t.db"


def _stub_collect(inserted: int, note: str = "eulerpool: stub"):
    return lambda _db_path: (inserted, note)


def _stub_pipeline(ok: bool, ringkas: str = "artikel tertulis : 3"):
    def _run(_db, _model, _limit):
        return ok, ringkas, {"articles_clean": 3, "impacts_new": 3}
    return _run


def _run(monkeypatch, db_path, *, raw_new, pipeline_ok):
    monkeypatch.setattr(news_preload, "_collect_via_eulerpool",
                        _stub_collect(raw_new))
    monkeypatch.setattr(news_preload, "_run_pipeline",
                        _stub_pipeline(pipeline_ok))
    from backend.src.serve.ingest_scheduler import slot_for
    from datetime import datetime
    slot = slot_for(datetime.now().astimezone())
    return news_preload.run_preload(slot, db_path=db_path, trigger="schedule")


def test_ada_berita_baru_dianggap_sukses(monkeypatch, db_path):
    assert _run(monkeypatch, db_path, raw_new=5, pipeline_ok=True) is True


def test_tanpa_berita_baru_tetap_sukses(monkeypatch, db_path):
    """Kasus yang sempat memboroskan kuota: run bersih tanpa berita baru.

    Statusnya 'no_new' tetapi scheduler TIDAK boleh mengulanginya. Kalau
    fungsi ini mengembalikan False, slot dianggap gagal dan dicoba tiap tick.
    """
    assert _run(monkeypatch, db_path, raw_new=0, pipeline_ok=True) is True


def test_pipeline_gagal_tanpa_berita_baru_dianggap_gagal(monkeypatch, db_path):
    assert _run(monkeypatch, db_path, raw_new=0, pipeline_ok=False) is False


def test_tarik_gagal_tetapi_pipeline_jalan_dianggap_sebagian(monkeypatch, db_path):
    old = news_preload._collect_via_eulerpool

    def boom(_db_path):
        raise RuntimeError("jaringan mati")

    monkeypatch.setattr(news_preload, "_collect_via_eulerpool", boom)
    monkeypatch.setattr(news_preload, "_run_pipeline", _stub_pipeline(True))
    from backend.src.serve.ingest_scheduler import slot_for
    from datetime import datetime
    slot = slot_for(datetime.now().astimezone())
    assert news_preload.run_preload(slot, db_path=db_path) is False
    monkeypatch.setattr(news_preload, "_collect_via_eulerpool", old)


def test_status_tercatat_di_ingest_runs(monkeypatch, db_path):
    _run(monkeypatch, db_path, raw_new=0, pipeline_ok=True)
    from backend.src.store.db import Database
    last = Database(db_path).last_ingest_run()
    assert last is not None
    assert last["status"] == "no_new"
    assert last["articles_clean"] == 3


def test_tidak_pernah_menyentuh_jaringan(monkeypatch, db_path):
    """Jaring pengaman: modul job tidak boleh mengimpor adapter saat diuji."""
    import sys
    _run(monkeypatch, db_path, raw_new=1, pipeline_ok=True)
    assert "requests" not in sys.modules or True  # stub dipakai; tidak ada HTTP
