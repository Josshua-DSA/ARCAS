"""Grafik simulasi tidak boleh menumpuk listener resize.

Empat giliran dulu menambah empat listener, masing-masing menahan instance
ECharts yang sudah tidak dipakai. Reset percakapan tidak melepas apa pun
karena hanya mengosongkan innerHTML. Dua-duanya bocor pelan-pelan sepanjang
sesi, jadi dijaga di sini.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path("frontend/GUI/src/js/pages/simulations.js")


def _src() -> str:
    return SRC.read_text(encoding="utf-8")


def test_listener_resize_dipasang_sekali_di_luar_gambar_grafik() -> None:
    """Satu listener global, bukan satu per grafik.

    Bentuk lama: `addEventListener("resize", function () { c.resize(); })`
    di dalam gambarGrafik -- satu listener per grafik, tak pernah dilepas.
    Bentuk baru: satu listener di pasang(), dijaga penanda `pasang._resize`.
    """
    src = _src()
    assert src.count('addEventListener("resize"') == 1
    assert "function () { c.resize(); }" not in src
    blok = src.split('addEventListener("resize"')[0]
    assert "pasang._resize" in blok[-400:]


def test_listener_resize_mengiterasi_semua_grafik() -> None:
    src = _src()
    blok = src.split('addEventListener("resize"')[1].split("});")[0]
    assert "for (var k in grafik)" in blok


def test_reset_melepas_instance_grafik() -> None:
    """simUlang harus dispose, bukan hanya mengosongkan innerHTML."""
    src = _src()
    blok = src.split('$("simUlang")')[1].split("setFase(1)")[0]
    assert "dispose()" in blok
    assert "grafik = {}" in blok


def test_dispose_menghapus_kunci_dari_peta() -> None:
    """Tanpa delete, kunci mati tetap ada dan ikut di-resize selamanya."""
    src = _src()
    blok = src.split("function gambarGrafik")[1].split("var info =")[0]
    assert re.search(r"delete grafik\[idKartu\]", blok)
