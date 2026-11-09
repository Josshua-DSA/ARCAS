"""Halaman muka di akar, dasbor di /overview.html.

Akar `/` dulu menyajikan dasbor. Setelah landing page ditambahkan, akar harus
menyajikan pengantar dan dasbor pindah ke `overview.html` — kalau tertukar,
pengunjung pertama mendarat langsung di grafik tanpa tahu apa yang dilihatnya.
"""
from __future__ import annotations

import re
from pathlib import Path

GUI = Path("frontend/GUI")


def _klien(tmp_path, monkeypatch):
    monkeypatch.setenv("ARCAS_DISABLE_SCHEDULER", "1")
    monkeypatch.setenv("ARCAS_WARMUP_TIMEOUT", "0")
    monkeypatch.setenv("ARCAS_DB_PATH", str(tmp_path / "uji.db"))
    from fastapi.testclient import TestClient

    from backend.src.serve.app import create_app

    return TestClient(create_app())


def test_akar_menyajikan_landing_bukan_dasbor(tmp_path, monkeypatch) -> None:
    with _klien(tmp_path, monkeypatch) as c:
        akar = c.get("/")
        assert akar.status_code == 200
        html = akar.text
        # Penanda landing: judul pengantar dan etalase empat halaman.
        assert "Skor sentimen berita diuji" in html
        assert "lp-targets" in html
        # Penanda dasbor yang TIDAK boleh ada di akar.
        assert "heroLead" not in html
        assert "targetTabs" not in html


def test_dasbor_tetap_terjangkau_di_overview(tmp_path, monkeypatch) -> None:
    with _klien(tmp_path, monkeypatch) as c:
        d = c.get("/overview.html")
        assert d.status_code == 200
        assert "heroLead" in d.text
        assert "targetTabs" in d.text


def test_landing_menautkan_ke_empat_halaman() -> None:
    html = (GUI / "index.html").read_text(encoding="utf-8")
    for tujuan in ("overview.html", "evidence.html", "research.html", "simulations.html"):
        assert f'href="{tujuan}' in html, f"landing tidak menautkan {tujuan}"


def test_dasbor_tidak_lagi_menautkan_index_sebagai_halaman() -> None:
    """Nav 4 halaman memakai overview.html; index.html hanya tautan merek."""
    for nama in ("overview", "evidence", "research", "simulations"):
        html = (GUI / f"{nama}.html").read_text(encoding="utf-8")
        assert 'data-page="index.html"' not in html, f"{nama} masih menandai index.html"
        assert 'data-page="overview.html"' in html, f"{nama} tidak punya nav ke dasbor"


def test_hotkey_memakai_overview() -> None:
    src = (GUI / "src/js/shell.js").read_text(encoding="utf-8")
    assert 'var PAGES = ["overview.html"' in src


def test_landing_tidak_memuat_shell_dasbor() -> None:
    """Landing tidak boleh menyeret shell.js: ia memuat splash dan ticker."""
    html = (GUI / "index.html").read_text(encoding="utf-8")
    assert "src/js/shell.js" not in html
    assert "src/js/splash.js" not in html
    assert re.search(r'src/js/pages/landing\.js', html)


def test_landing_tidak_mengarang_angka() -> None:
    """Angka cakupan hanya dari /api/meta; tidak ada angka mati di markup."""
    html = (GUI / "index.html").read_text(encoding="utf-8")
    # Kartu fakta diisi JS, jadi di markup hanya ada placeholder.
    assert "lp-fact-note" in html
    # Tidak ada angka cakupan yang ditulis langsung.
    assert not re.search(r"lp-fact-value[^>]*>\s*\d", html)
