"""Skeleton pergantian aset: tidak boleh berkedip, tidak boleh nyangkut.

Dua ambang yang dijaga:
  GRACE 120ms  API balas <25ms, jadi skeleton tidak boleh muncul untuk
               pergantian biasa. Kalau muncul, setiap klik tab berkedip.
  MIN   320ms  Sekali muncul, harus bertahan cukup lama untuk terbaca.

Selain itu skeleton hanya boleh menyentuh isi panel: header, tab, dan judul
tetap diam. `fadeLalu` lama memudarkan seluruh body, itulah yang diganti.
"""
from __future__ import annotations

import re
from pathlib import Path

SHELL = Path("frontend/GUI/src/js/shell.js")
CSS = Path("frontend/GUI/src/css/layout.css")


def _skeleton() -> str:
    """Ambang GRACE/MIN dideklarasikan tepat sebelum fungsinya, jadi blok
    diambil dari deklarasi ambang sampai penutup fungsi."""
    src = SHELL.read_text(encoding="utf-8")
    return src[src.index("var GRACE"):src.index("A.skeletonLalu")]


def test_skeleton_selalu_tampil() -> None:
    """Grace 120ms mematikan animasinya sendiri: API balas 17-74ms, lebih cepat
    dari grace, jadi konten cuma ditukar seketika (blip, bukan gerak)."""
    blok = _skeleton()
    assert re.search(r"GRACE\s*=\s*0", blok)
    assert "setTimeout(buka, GRACE)" in blok


def test_ada_durasi_minimum() -> None:
    blok = _skeleton()
    assert re.search(r"MIN\s*=\s*240", blok)
    assert "tayang = tampil ? MIN : 0" in blok


def test_ganti_aset_memakai_skeleton_bukan_fade() -> None:
    """fadeLalu memudarkan seluruh body termasuk tab; skeleton tidak."""
    src = SHELL.read_text(encoding="utf-8")
    blok = src.split("function selectTarget")[1].split("function bindTabs")[0]
    assert "skeletonLalu(" in blok
    assert "fadeLalu(" not in blok


def test_pindah_halaman_tetap_memakai_fade() -> None:
    """Fade masuk akal saat konteks benar-benar berganti (halaman lain)."""
    src = SHELL.read_text(encoding="utf-8")
    assert src.count("fadeLalu(function () { location.href") >= 2


def test_reduced_motion_melewati_skeleton() -> None:
    assert "if (reduce) { kerja(); return; }" in _skeleton()


def test_isi_panel_diberi_animasi_masuk() -> None:
    """Skeleton saja tidak cukup: setelah data tiba, isi panel harus masuk
    dengan gerak. Tanpa ini konten ditukar seketika dan terbaca sebagai blip."""
    blok = _skeleton()
    assert "masukPanel()" in blok
    css = CSS.read_text(encoding="utf-8")
    assert "@keyframes arcas-masuk" in css
    assert ".panel-body.is-masuk" in css


def test_teks_memudar_bukan_dipotong() -> None:
    """Tanpa transisi color, kalimat hilang dalam satu frame = kedipan."""
    css = CSS.read_text(encoding="utf-8")
    assert "transition:color .16s ease" in css


def test_kelas_dilepas_walau_promise_gagal() -> None:
    """Ganti target cepat membatalkan request; skeleton tidak boleh tertinggal."""
    blok = _skeleton()
    assert "hasil.then(akhir, akhir)" in blok


def test_css_tidak_memakai_no_repeat() -> None:
    """background-size 200% + no-repeat membuat gradien keluar layar sebagian
    siklus, jadi batang berkedip hilang-timbul (terukur 2,6% cakupan)."""
    css = CSS.read_text(encoding="utf-8")
    blok = css.split("@keyframes arcas-skl")[1].split(".hero,")[0]
    assert "no-repeat" not in blok


def test_grafik_tidak_menambah_tinggi() -> None:
    """::before setinggi 340px menambah tinggi panel (1087px vs 735px)."""
    css = CSS.read_text(encoding="utf-8")
    blok = css.split("@keyframes arcas-skl")[1].split(".hero,")[0]
    # Komentar menyebut ::before sebagai catatan sejarah; yang dilarang selector.
    assert "::before{" not in blok


def test_tab_tidak_ikut_diredupkan() -> None:
    css = CSS.read_text(encoding="utf-8")
    blok = css.split("@keyframes arcas-skl")[1].split(".hero,")[0]
    assert ".target-tab" not in blok
    assert "header" not in blok
