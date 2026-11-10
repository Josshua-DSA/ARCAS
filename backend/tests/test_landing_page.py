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


def test_landing_menautkan_ke_tiga_tujuan_nav() -> None:
    """Nav atas: Pricing, Documentation, Contribute. Tombol kepala ke dasbor."""
    html = (GUI / "index.html").read_text(encoding="utf-8")
    for tujuan in ("pricing.html", "documentation.html", "github.com/Josshua-DSA/ARCAS"):
        assert tujuan in html, f"landing tidak menautkan {tujuan}"
    # Tombol kepala menuju dasbor.
    assert 'href="overview.html">Explore' in html


def test_pricing_tersaji_dan_bernavigasi_sama() -> None:
    halaman = (GUI / "pricing.html").read_text(encoding="utf-8")
    assert "lp-tier-grid" in halaman
    for tujuan in ("pricing.html", "documentation.html", "github.com/Josshua-DSA/ARCAS"):
        assert tujuan in halaman, f"pricing tidak menautkan {tujuan}"


def test_dokumentasi_memuat_sebelas_endpoint() -> None:
    """Halaman docs harus mencantumkan setiap route yang benar-benar ada.

    Kalau route ditambah di app.py tanpa memperbarui halaman ini, dokumentasi
    berbohong — lebih buruk daripada tidak punya dokumentasi.
    """
    docs = (GUI / "documentation.html").read_text(encoding="utf-8")
    rute = ("/health", "/api/meta", "/api/universe", "/api/series/{target}",
            "/api/impacts/{target}", "/api/stats/{target}", "/api/allocation",
            "/api/persona/{article_id}", "/api/simulate",
            "/api/simulate/{run_id}", "/api/preload/status")
    for r in rute:
        assert r in docs, f"documentation.html tidak mencantumkan {r}"


def test_tidak_ada_tautan_dokumentasi_ke_localhost() -> None:
    """Tautan navigasi tidak boleh menunjuk localhost: pengunjung lain akan
    kena ERR_CONNECTION_REFUSED. Contoh curl di dalam docs dikecualikan."""
    for nama in ("index.html", "pricing.html", "overview.html", "evidence.html",
                 "research.html", "simulations.html"):
        html = (GUI / nama).read_text(encoding="utf-8")
        assert "localhost:8000" not in html, f"{nama} masih menautkan localhost"


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


def test_setiap_halaman_punya_skip_link() -> None:
    """Skip link wajib: nav 5 tautan berarti 5 Tab sebelum konten.

    Tanpa ini pengguna keyboard harus melewati seluruh nav di setiap halaman.
    Target diperiksa harus benar-benar ada — `simulations.html` memakai
    `id="simRoot"` yang dipakai 91 selektor, jadi tidak boleh dipaksa `main`.
    """
    for nama in ("index.html", "overview.html", "evidence.html",
                 "research.html", "simulations.html", "pricing.html"):
        html = (GUI / nama).read_text(encoding="utf-8")
        assert 'class="skip-link"' in html, f"{nama} tanpa skip link"
        cocok = re.search(r'class="skip-link" href="#([\w-]+)"', html)
        assert cocok, f"{nama} skip link tanpa target"
        target = cocok.group(1)
        assert f'id="{target}"' in html, f"{nama} skip link ke #{target} yang tidak ada"
