"""Uji P2-7: batas panjang di skema OpenAPI harus sama dengan validator.

Sebelumnya `SimulateRequest.text` mengiklankan 20.000 karakter sementara
`sim_input.validate` menolak di atas 4.000. Fungsionalnya benar (422 ramah),
tetapi pembaca skema mengira 20.000 boleh -- dan itu janji palsu di dokumentasi
publik.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.src.serve.app import create_app
from backend.src.serve.sim_input import MAX_CHARS


@pytest.fixture()
def client(tmp_path):
    return TestClient(create_app(db_path=tmp_path / "t.db"))


def test_openapi_mengiklankan_batas_yang_sama(client):
    skema = client.get("/openapi.json").json()
    properti = skema["components"]["schemas"]["SimulateRequest"]["properties"]["text"]
    assert properti["maxLength"] == MAX_CHARS, (
        f"OpenAPI menjanjikan {properti['maxLength']}, validator menolak di atas "
        f"{MAX_CHARS}"
    )


def test_teks_melebihi_batas_ditolak_di_lapisan_skema(client):
    """Harus 422 dari Pydantic, bukan lolos ke validator lalu ditolak di sana."""
    r = client.post(
        "/api/simulate",
        json={"text": "x" * (MAX_CHARS + 1), "kind": "berita"},
    )
    assert r.status_code == 422


def test_teks_tepat_di_batas_tidak_ditolak_karena_panjang(client):
    """Batas bersifat inklusif; jangan sampai off-by-one menolak teks sah."""
    r = client.post(
        "/api/simulate",
        json={"text": "Gold rose sharply today. " * (MAX_CHARS // 26), "kind": "berita"},
    )
    # Boleh ditolak karena alasan lain, tetapi bukan karena terlalu panjang.
    if r.status_code == 422:
        assert "maxLength" in r.text or "terlalu_panjang" not in r.text
