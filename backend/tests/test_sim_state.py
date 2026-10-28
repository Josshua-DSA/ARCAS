"""Uji P2-8 dan P2-9 tanpa memuat bobot model.

Keduanya cacat pada `SimulationService` yang dipakai BERSAMA antar request.
Model asli tidak diperlukan: yang diuji adalah bagaimana `analyze` memperlakukan
state bersama dan bagaimana ia melaporkan kegagalan routing.
"""
from __future__ import annotations

import threading

from backend.src.serve.sim_service import SimulationService

BERITA = "Gold surged 3.2% to a record high as the dollar weakened sharply."


class _ModelPalsu:
    """Model cukup untuk melewati jalur skoring tanpa bobot sungguhan."""

    model_version = "palsu-1"

    def __init__(self, skor: float = 0.8):
        self._skor = skor

    def score_article(self, _id, _teks):
        from types import SimpleNamespace

        return SimpleNamespace(score=self._skor, tone=SimpleNamespace(value="positive"))


def _siapkan(skor=0.8):
    """Service dengan model palsu di cache untuk SEMUA entri PRIORITAS.

    Nama kunci harus persis sama dengan PRIORITAS (`finbert_emas`, bukan
    `xau_finbert`); salah nama membuat `_pilih_model` memuat bobot sungguhan.
    """
    svc = SimulationService(db_path=":memory:")
    for nama, _pemuat, _space in SimulationService.PRIORITAS:
        svc._cache[nama] = _ModelPalsu(skor)
    svc._model_router = None
    return svc


# -- P2-8: state bersama tidak boleh bocor antar request -------------------


def test_analyze_tidak_menyisakan_state_instance():
    """Setelah analyze, tidak boleh ada sisa nilai yang bisa dibaca request lain.

    Sebelum P2-8, `_degraded` dan `_score_space` ditulis ke instance lalu dibaca
    di akhir fungsi. Karena rute `def` sinkron berjalan di threadpool, request
    lain bisa menimpanya di tengah jalan.
    """
    svc = _siapkan()
    svc.analyze(BERITA, "berita")

    assert getattr(svc, "_score_space", None) is None, (
        "skor_space masih tersimpan di instance"
    )


def test_dua_request_paralel_tidak_saling_menimpa(monkeypatch):
    """Bukti langsung: analyze paralel harus mengembalikan hasil yang konsisten.

    Tanpa variabel lokal, nilai `_score_space`/`_degraded` milik satu request
    bisa terbaca oleh request lain, sehingga arah dan peringatan tercampur.
    """
    svc = _siapkan()

    hasil: list = []
    kunci = threading.Lock()
    mulai = threading.Barrier(8)

    def jalankan():
        mulai.wait()
        r = svc.analyze(BERITA, "berita")
        with kunci:
            hasil.append(r)

    utas = [threading.Thread(target=jalankan) for _ in range(8)]
    for t in utas:
        t.start()
    for t in utas:
        t.join()

    assert len(hasil) == 8
    # Semua request memakai input identik -> hasil harus identik. Kalau state
    # bocor, salah satu akan membawa peringatan/degraded milik yang lain.
    assert len({r.direction for r in hasil}) == 1
    assert len({tuple(r.warnings) for r in hasil}) == 1


# -- P2-9: routing gagal tidak boleh menyamar sebagai "netral" ------------


def test_routing_gagal_memberi_peringatan(monkeypatch):
    """Kegagalan routing harus terlihat di `warnings`, bukan diam-diam netral."""
    svc = _siapkan()

    def boom(_self):
        raise RuntimeError("router rusak")

    monkeypatch.setattr(SimulationService, "_ensure_router", boom)
    r = svc.analyze(BERITA, "berita")

    assert r.direction == "netral"  # nilai jatuhannya tetap netral
    assert any("routing gagal" in w.lower() for w in r.warnings), (
        f"kegagalan routing tidak dilaporkan: {r.warnings}"
    )
    assert any("router rusak" in w for w in r.warnings)


def test_netral_karena_analisis_tidak_berperingatan_routing():
    """Kebalikannya: netral yang wajar tidak boleh diberi peringatan palsu."""
    svc = _siapkan(skor=0.0)  # skor netral
    r = svc.analyze(BERITA, "berita")
    assert not any("routing gagal" in w.lower() for w in r.warnings)
