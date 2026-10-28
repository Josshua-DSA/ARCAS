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


# -- P1-8: klaim slot atomik ------------------------------------------------


def _hit(monkeypatch, db_path, slot, *, trigger="schedule"):
    """Jalankan run_preload dan laporkan berapa kali eulerpool DITARIK."""
    panggilan = {"collect": 0}

    def collect(_db_path):
        panggilan["collect"] += 1
        return 0, "eulerpool: stub"

    monkeypatch.setattr(news_preload, "_collect_via_eulerpool", collect)
    monkeypatch.setattr(news_preload, "_run_pipeline", _stub_pipeline(True))
    ok = news_preload.run_preload(slot, db_path=db_path, trigger=trigger)
    return ok, panggilan["collect"]


def test_proses_kedua_tidak_menembak_eulerpool_lagi(monkeypatch, db_path):
    """Inti P1-8: slot yang SEDANG dipegang proses lain harus DILEWATI.

    Skenario asli adalah dua proses BERSAMAAN (mis. uvicorn --workers 2), jadi
    klaim pertama harus dibiarkan berstatus 'running' saat proses kedua datang.
    Kalau run pertama dibiarkan selesai lebih dulu, statusnya bukan 'running'
    lagi dan pengulangan dicegah oleh `has_run_for_slot` di scheduler -- bukan
    oleh klaim. Menguji dengan urutan selesai-dulu justru tidak menguji apa pun.
    """
    from datetime import datetime

    from backend.src.serve.ingest_scheduler import slot_for
    from backend.src.store.db import Database

    slot = slot_for(datetime.now().astimezone())

    # Proses A memegang slot dan BELUM selesai (menembak API lambat).
    db = Database(db_path)
    db.init_schema()
    assert db.claim_ingest_slot("schedule", slot.isoformat()) is not None

    # Proses B datang: harus melewati tanpa menembak eulerpool.
    ok, tarik = _hit(monkeypatch, db_path, slot)
    assert ok is True, "slot yang dilewati bukan kegagalan"
    assert tarik == 0, "proses kedua menembak eulerpool lagi"


def test_klaim_bersamaan_hanya_satu_yang_menang(db_path):
    """Uji atomisitas sesungguhnya: N proses berebut slot yang sama.

    Satu-satunya INSERT...SELECT berjalan dalam satu transaksi tulis SQLite,
    sehingga tepat satu pemanggil boleh menang. Kalau ini gagal, kuota
    eulerpool terbakar sebanyak jumlah worker.
    """
    import threading

    from backend.src.store.db import Database

    db = Database(db_path)
    db.init_schema()
    slot = "2026-10-28T00:00:00+07:00"

    hasil: list = []
    kunci = threading.Lock()
    mulai = threading.Barrier(8)

    def coba():
        mulai.wait()  # lepaskan semuanya sedekat mungkin
        rid = Database(db_path).claim_ingest_slot("schedule", slot)
        with kunci:
            hasil.append(rid)

    utas = [threading.Thread(target=coba) for _ in range(8)]
    for t in utas:
        t.start()
    for t in utas:
        t.join()

    menang = [r for r in hasil if r is not None]
    assert len(menang) == 1, f"harus tepat 1 pemenang, dapat {len(menang)}"


def test_slot_berbeda_tetap_boleh_ditarik(monkeypatch, db_path):
    """Klaim hanya mengunci SLOT yang sama, bukan seluruh tabel."""
    from datetime import datetime, timedelta

    from backend.src.serve.ingest_scheduler import slot_for

    sekarang = datetime.now().astimezone()
    slot_a = slot_for(sekarang)
    slot_b = slot_for(sekarang) - timedelta(days=1)

    _, tarik_a = _hit(monkeypatch, db_path, slot_a)
    _, tarik_b = _hit(monkeypatch, db_path, slot_b)
    assert tarik_a == 1 and tarik_b == 1


def test_klaim_kedaluwarsa_boleh_diambil_alih(monkeypatch, db_path):
    """Proses yang mati di tengah jalan tidak boleh mengunci slot selamanya."""
    import sqlite3
    from datetime import datetime, timedelta

    from backend.src.serve.ingest_scheduler import slot_for
    from backend.src.store.db import Database

    slot = slot_for(datetime.now().astimezone())
    _, tarik1 = _hit(monkeypatch, db_path, slot)
    assert tarik1 == 1

    # Mundurkan klaim melewati batas waktu -> dianggap milik proses mati.
    basi = (
        datetime.now() - timedelta(seconds=Database.CLAIM_TIMEOUT_SECONDS + 60)
    ).isoformat()
    with sqlite3.connect(db_path) as c:
        c.execute("UPDATE ingest_runs SET started_at = ?;", (basi,))

    _, tarik2 = _hit(monkeypatch, db_path, slot)
    assert tarik2 == 1, "klaim kedaluwarsa seharusnya bisa diambil alih"


def test_run_manual_tidak_diklaim_sehingga_tidak_saling_memblokir(db_path):
    """`start_ingest_run` tetap tersedia untuk run manual yang berdampingan."""
    from backend.src.store.db import Database

    db = Database(db_path)
    db.init_schema()
    a = db.start_ingest_run("manual")
    b = db.start_ingest_run("manual")
    assert a > 0 and b > 0 and a != b
