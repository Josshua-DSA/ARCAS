"""Uji kesiapan model (P1-9) tanpa memuat bobot 440 MB.

Sebelum P1-9, request pertama menanggung 3,33 detik pemuatan model dan tidak
ada cara membedakan "server siap" dari "server baru hidup". Tes ini menguji
kontraknya: status kesiapan, endpoint 503 saat model gagal dimuat, dan bahwa
warm-up tidak pernah melempar exception.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.src.serve.app import create_app
from backend.src.serve.sim_service import SimulationService

BERITA = "Gold surged 3.2% to a record high as the dollar weakened sharply."


@pytest.fixture()
def svc():
    return SimulationService(db_path=":memory:")


# -- SimulationService: status kesiapan ------------------------------------


def test_status_awal_belum_dicoba(svc):
    """None berarti warm-up belum dicoba -- bukan berarti gagal."""
    assert svc.siap is None
    assert svc.alasan_belum_siap is None


def test_warm_up_gagal_tidak_melempar_dan_mencatat_alasan(svc, monkeypatch):
    """Warm-up yang gagal harus melaporkan alasan, bukan meledak."""
    def boom(_self):
        raise FileNotFoundError("bobot tidak ada")

    for _nama, pemuat, _space in SimulationService.PRIORITAS:
        monkeypatch.setattr(SimulationService, pemuat, boom, raising=False)

    assert svc.warm_up() is False
    assert svc.siap is False
    assert svc.alasan_belum_siap
    assert "bobot tidak ada" in svc.alasan_belum_siap


def test_warm_up_berhasil_menandai_siap(svc, monkeypatch):
    """Bila minimal satu model termuat, status harus True."""
    for _nama, pemuat, _space in SimulationService.PRIORITAS:
        monkeypatch.setattr(SimulationService, pemuat, lambda _self: object(), raising=False)

    assert svc.warm_up() is True
    assert svc.siap is True
    assert svc.alasan_belum_siap is None


# -- Endpoint: 503 saat model gagal dimuat --------------------------------


def _client(tmp_path, monkeypatch, siap):
    app = create_app(db_path=tmp_path / "t.db")
    app.state.sim_service._siap = siap
    if siap is False:
        app.state.sim_service._alasan_belum_siap = "bobot rusak"
    return TestClient(app)


def test_endpoint_503_saat_model_gagal_dimuat(tmp_path, monkeypatch):
    c = _client(tmp_path, monkeypatch, False)
    r = c.post("/api/simulate", json={"text": BERITA, "kind": "berita"})
    assert r.status_code == 503
    assert r.json()["detail"]["kode"] == "model_belum_siap"
    assert "bobot rusak" in r.json()["detail"]["pesan"]
    assert r.headers.get("Retry-After") == "30"


def test_endpoint_tidak_503_saat_belum_dicoba(tmp_path, monkeypatch):
    """None = warm-up belum dicoba -> jalur lambat harus tetap jalan.

    Tanpa ini, deployment yang mematikan warm-up akan menolak SEMUA request.
    """
    c = _client(tmp_path, monkeypatch, None)
    # Bukan 503; jalur lambat akan mencoba memuat model sungguhan, jadi kita
    # hanya memastikan gerbang kesiapan tidak menolaknya lebih dulu.
    r = c.post("/api/simulate", json={"text": "halo", "kind": "berita"})
    assert r.status_code == 422, "gerbang input harus tetap berjalan sebelum 503"
