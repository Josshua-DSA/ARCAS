"""Uji endpoint /api/simulate: gerbang, kontrak respons, dan penolakan."""

import pytest
from fastapi.testclient import TestClient

from backend.src.serve.app import create_app

pytestmark = pytest.mark.slow

BERITA = (
    "Gold surged 3.2% to a record high as the dollar collapsed and investors "
    "rushed into bullion as a safe haven."
)
RUMOR = (
    "Kabarnya ada bank sentral besar yang menambah cadangan emas bulan ini, "
    "menurut sumber yang enggan disebut namanya."
)


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_obrolan_ditolak_422_dengan_kode(client):
    r = client.post("/api/simulate", json={"text": "halo", "kind": "berita"})
    assert r.status_code == 422
    assert r.json()["detail"]["kode"] == "obrolan"


def test_pertanyaan_ditolak_422_dengan_kode(client):
    r = client.post(
        "/api/simulate", json={"text": "Besok emas naik nggak?", "kind": "berita"}
    )
    assert r.status_code == 422
    assert r.json()["detail"]["kode"] == "pertanyaan"


def test_kind_wajib_diisi(client):
    """Tanpa `kind`, permintaan harus gagal -- bukan dianggap berita."""
    r = client.post("/api/simulate", json={"text": BERITA})
    assert r.status_code == 422


def test_kind_tidak_boleh_selain_berita_atau_rumor(client):
    r = client.post("/api/simulate", json={"text": BERITA, "kind": "opini"})
    assert r.status_code == 422


def test_berita_menghasilkan_kontrak_lengkap(client):
    r = client.post("/api/simulate", json={"text": BERITA, "kind": "berita"})
    assert r.status_code == 200
    j = r.json()
    for kunci in (
        "input_kind", "is_rumor", "tone", "score", "confidence",
        "confidence_raw", "penalty", "direction", "model_version",
        "summary", "warnings", "degraded", "disclaimer", "stances",
    ):
        assert kunci in j, f"field '{kunci}' hilang dari respons"
    assert j["input_kind"] == "berita"
    assert j["is_rumor"] is False
    assert j["penalty"] == 1.0
    assert len(j["stances"]) == 5
    assert j["disclaimer"]


def test_rumor_memakai_penalti_dan_menandai_dirinya(client):
    r = client.post("/api/simulate", json={"text": RUMOR, "kind": "rumor"})
    assert r.status_code == 200
    j = r.json()
    assert j["is_rumor"] is True
    assert j["penalty"] == 0.60
    assert j["confidence"] < j["confidence_raw"]


def test_sumber_diteruskan_dan_menghapus_peringatan(client):
    r = client.post(
        "/api/simulate",
        json={"text": RUMOR, "kind": "rumor", "source": "Reuters"},
    )
    j = r.json()
    assert j["source"] == "Reuters"
    assert not any("tanpa sumber" in w.lower() for w in j["warnings"])


def test_teks_kosong_ditolak(client):
    r = client.post("/api/simulate", json={"text": "", "kind": "berita"})
    assert r.status_code == 422


def test_target_tidak_dikenal_ditolak_422(client):
    """Target di luar 3 aset terkunci harus DITOLAK, bukan jadi "netral".

    Regresi: sebelumnya `target` hanya `str` tanpa validasi, sehingga "GOLD"
    (nama yang wajar bagi pengguna) lolos ke routing, tidak cocok dengan apa
    pun, lalu keluar sebagai direction="netral" tanpa peringatan. Pengguna
    membaca "netral" sebagai hasil analisis padahal targetnya tidak dikenali.
    """
    r = client.post(
        "/api/simulate", json={"text": BERITA, "kind": "berita", "target": "GOLD"}
    )
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail["kode"] == "target_tidak_dikenal"
    # Pesan harus menyebut pilihan yang sah, bukan sekadar "invalid".
    assert "XAU" in detail["pesan"] and "SPX" in detail["pesan"]
    assert set(detail["contoh"]) == {"XAU", "RATE_UST", "SPX"}


def test_target_tidak_dikenal_kosong_maupun_spasi_ditolak(client):
    for t in ("", "   ", "BANANA", "xau_usd"):
        r = client.post(
            "/api/simulate", json={"text": BERITA, "kind": "berita", "target": t}
        )
        assert r.status_code == 422, t
        assert r.json()["detail"]["kode"] == "target_tidak_dikenal", t


def test_target_huruf_kecil_dinormalkan_ke_ejaan_resmi(client):
    """`xau` tetap diterima, tetapi respons memakai ejaan resmi `XAU`."""
    r = client.post(
        "/api/simulate", json={"text": BERITA, "kind": "berita", "target": "xau"}
    )
    assert r.status_code == 200
    assert r.json()["target"] == "XAU"


def test_target_bawaan_adalah_xau(client):
    r = client.post("/api/simulate", json={"text": BERITA, "kind": "berita"})
    assert r.status_code == 200
    assert r.json()["target"] == "XAU"
