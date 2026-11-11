"""Transisi pergantian aset: konten masuk bertahap, bukan ditukar seketika.

Riwayat pendekatan, semuanya terukur:

1. `fadeLalu` — memudarkan SELURUH body termasuk header dan tab. Setiap klik
   aset terasa seperti halaman memuat ulang.
2. `skeletonLalu` dengan GRACE 120ms — skeleton tidak pernah tampil, karena
   API balas 17-74ms. Konten cuma ditukar seketika: blip.
3. `skeletonLalu` dengan GRACE 0 + MIN 240ms — skeleton tampil, tapi layar
   sempat dikosongkan. Masih terbaca sebagai kedipan.
4. **Sekarang**: stagger fade seperti daftar berita di Home. Konten baru
   langsung ada dan memudar masuk bertahap. Tidak ada placeholder, tidak ada
   layar kosong, tidak ada teks yang disembunyikan.

Tes ini mengunci pendekatan ke-4 supaya tidak mundur ke skeleton.
"""
from __future__ import annotations

from pathlib import Path

SHELL = Path("frontend/GUI/src/js/shell.js")
CSS = Path("frontend/GUI/src/css/layout.css")


def _masuk() -> str:
    src = SHELL.read_text(encoding="utf-8")
    return src[src.index("function masukLalu"):src.index("A.masukLalu = masukLalu")]


def test_ganti_aset_memakai_stagger_bukan_fade_seluruh_body() -> None:
    src = SHELL.read_text(encoding="utf-8")
    blok = src.split("function selectTarget")[1].split("function bindTabs")[0]
    assert "masukLalu(" in blok
    assert "fadeLalu(" not in blok


def test_tidak_ada_lagi_skeleton() -> None:
    """Skeleton mengosongkan layar lebih dulu, itu sumber kedipan."""
    src = SHELL.read_text(encoding="utf-8")
    assert "skeletonLalu" not in src
    assert "is-skl" not in src
    css = CSS.read_text(encoding="utf-8")
    assert "is-skl" not in css
    assert "arcas-skl" not in css


def test_pindah_halaman_tetap_memakai_fade() -> None:
    """Fade masuk akal saat konteks benar-benar berganti (halaman lain)."""
    src = SHELL.read_text(encoding="utf-8")
    assert src.count("fadeLalu(function () { location.href") >= 2


def test_reduced_motion_melewati_transisi() -> None:
    assert "if (reduce) { kerja(); return; }" in _masuk()


def test_kelas_dipasang_setelah_render() -> None:
    """Kalau dipasang sebelum render, animasi menghabiskan dirinya di DOM lama."""
    assert "hasil.then(tandai" in _masuk()


def test_stagger_memakai_pola_yang_sama_dengan_daftar_berita() -> None:
    """Transisi Home: `arcas-fade` + delay bertingkat per anak."""
    css = CSS.read_text(encoding="utf-8")
    blok = css.split(".rl-masuk{")[1].split("@media")[0]
    assert "arcas-fade" in blok
    for n in range(1, 6):
        assert f".rl-masuk > *:nth-child({n})" in blok


def test_reduced_motion_mematikan_stagger() -> None:
    css = CSS.read_text(encoding="utf-8")
    assert ".rl-masuk > *{animation:none}" in css


def test_tidak_mengosongkan_layar() -> None:
    """Tidak ada aturan yang menyembunyikan isi panel saat transisi. Teks
    transparan dan visibility:hidden adalah cara skeleton lama, bukan sekarang."""
    css = CSS.read_text(encoding="utf-8")
    assert "color:transparent!important" not in css
    assert "visibility:hidden" not in css
