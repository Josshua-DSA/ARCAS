"""Fade halaman tidak boleh dipotong animationend milik elemen anak.

`.panel` dan `.news-item` memakai animasi `arcas-rise` yang berdurasi 500ms.
Event `animationend`-nya menggelembung ke `body`, tempat `fadeLalu` mendengar.
Tanpa cek `e.target`, satu panel yang selesai animasi di tengah fade memotong
fade di 40ms -- terukur opacity 0,68 lalu langsung memudar masuk lagi.
"""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path("frontend/GUI/src/js/shell.js")


def _src() -> str:
    return SRC.read_text(encoding="utf-8")


def _fade_lalu() -> str:
    return SRC.read_text(encoding="utf-8").split("function fadeLalu")[1].split("A.fadeLalu")[0]


def test_handler_menolak_event_dari_anak() -> None:
    blok = _fade_lalu()
    assert re.search(r"if \(e && e\.target !== b\) return;", blok)


def test_handler_menerima_argumen_event() -> None:
    """Tanpa parameter, event tidak bisa diperiksa asalnya."""
    assert re.search(r"function jalan\(e\)", _fade_lalu())


def test_fade_out_dilepas_sebelum_fade_in_dipasang() -> None:
    blok = _fade_lalu()
    pos_lepas = blok.index('b.classList.remove("is-fading-out")')
    pos_pasang = blok.index('b.classList.add("is-fading-in")')
    assert pos_lepas < pos_pasang


def test_reduced_motion_melewati_fade_sepenuhnya() -> None:
    blok = _fade_lalu()
    assert "if (reduce" in blok
    assert "if (kerja) kerja(); return;" in blok


def test_reflow_dipaksa_sebelum_animasi_mulai() -> None:
    """Tanpa reflow, browser bisa menggabungkan dua state dan animasi tak jalan."""
    assert "void b.offsetHeight" in _fade_lalu()
