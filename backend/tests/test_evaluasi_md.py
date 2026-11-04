"""Dokumen evaluasi tidak boleh mengarang angka saat artefak tidak ada.

Aturan proyek: data yang tidak tersedia ditulis "tidak tersedia", bukan nol.
Kalau ini bocor, dosen/penguji membaca 0.0000 sebagai hasil pengukuran.
"""

import importlib.util
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "evaluasi_model.py"


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("evaluasi_model", _SCRIPT)
    assert spec and spec.loader, f"skrip tidak ditemukan: {_SCRIPT}"
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_artefak_kosong_menulis_tidak_tersedia_bukan_nol(mod):
    teks = mod.bagian_xau({}, {})
    assert "tidak tersedia" in teks.lower()
    assert "0.0000" not in teks


def test_fomc_tanpa_metrik_tidak_mengarang(mod):
    teks = mod.bagian_fomc({})
    assert "tidak tersedia" in teks.lower()
    assert "| Akurasi |" not in teks


def test_angka_none_jadi_tidak_tersedia(mod):
    assert mod.angka(None) == "tidak tersedia"
    assert mod.angka(0.951744) == "0.9517"
