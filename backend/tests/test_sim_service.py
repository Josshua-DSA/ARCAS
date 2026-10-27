"""Uji simulasi end-to-end dengan model sungguhan.

Uji ini memuat bobot FinBERT-EMAS (~440 MB) sehingga ditandai `slow`. Yang
diuji bukan akurasi model, melainkan **integritas alur**: skor dari bobot
benar-benar mengalir ke stance persona, rumor benar-benar diturunkan, dan
obrolan benar-benar ditolak sebelum menyentuh model.
"""
from __future__ import annotations

import pytest

from backend.src.serve.sim_input import InputRejected
from backend.src.serve.sim_service import SimulationService

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def service():
    return SimulationService()


# --- gerbang bekerja sebelum model disentuh -------------------------------

@pytest.mark.parametrize("teks", [
    "halo",
    "Besok emas naik nggak?",
    "Menurutmu harga emas akan naik?",
])
def test_obrolan_ditolak_tanpa_memuat_model(teks):
    """Penolakan harus terjadi sebelum model dimuat.

    Service baru tanpa model: bila gerbang gagal, uji ini akan mencoba memuat
    bobot 440 MB dan melambat drastis. Cepatnya uji menandakan gerbang benar.
    """
    s = SimulationService()
    with pytest.raises(InputRejected):
        s.analyze(teks, "berita")
    # Model tidak boleh termuat gara-gara input sampah.
    assert s._model is None


# --- alur penuh -----------------------------------------------------------

BERITA_KUAT_POS = (
    "Gold surged 3.2% to a record high as the dollar collapsed and investors "
    "rushed into bullion as a safe haven amid sharp equity losses."
)


def test_alur_penuh_menghasilkan_lima_persona(service):
    r = service.analyze(BERITA_KUAT_POS, "berita", target="XAU")
    assert len(r.stances) == 5
    assert r.score > 0
    assert r.confidence > 0
    assert r.direction in ("bullish", "bearish", "netral", "neutral")
    assert r.summary
    assert r.disclaimer


def test_sinyal_kuat_membuat_persona_berbeda_pendapat(service):
    """Bukti utama bahwa bobot benar-benar dipakai.

    Bila model diabaikan dan skor dikarang, kelima persona akan selalu sama.
    """
    r = service.analyze(BERITA_KUAT_POS, "berita", target="XAU")
    stance = {s.stance for s in r.stances}
    assert "buy" in stance
    assert len(stance) > 1, "persona seharusnya tidak seragam pada sinyal kuat"


def test_sinyal_negatif_kuat_menghasilkan_jual(service):
    teks = (
        "Gold plunged 4% as the dollar strengthened sharply and investors "
        "dumped bullion amid a broad sell-off in commodity markets."
    )
    r = service.analyze(teks, "berita", target="XAU")
    assert r.score < 0
    assert any(s.stance == "sell" for s in r.stances)


def test_teks_datar_semua_menahan(service):
    teks = (
        "Gold steadied near $4,120 in quiet trading as investors waited for "
        "the next Federal Reserve decision on interest rates."
    )
    r = service.analyze(teks, "berita", target="XAU")
    assert all(s.stance == "hold" for s in r.stances)


# --- rumor diturunkan ----------------------------------------------------

RUMOR = (
    "Kabarnya ada bank sentral besar yang menambah cadangan emas bulan ini, "
    "menurut sumber yang enggan disebut namanya."
)


def test_rumor_menurunkan_keyakinan_dibanding_berita(service):
    berita = service.analyze(BERITA_KUAT_POS, "berita", target="XAU")
    rumor = service.analyze(RUMOR, "rumor", target="XAU")
    assert rumor.penalty == 0.60
    assert rumor.confidence < rumor.confidence_raw
    # Penurunan harus mengikuti faktor, bukan angka karangan. Toleransi 1e-3
    # karena `confidence` dibulatkan 4 desimal untuk tampilan.
    assert abs(rumor.confidence - rumor.confidence_raw * 0.60) < 1e-3


def test_rumor_tanpa_sumber_diberi_peringatan(service):
    r = service.analyze(RUMOR, "rumor", target="XAU")
    assert any("sumber" in w.lower() for w in r.warnings)


def test_berita_tanpa_sumber_tidak_diberi_peringatan_sumber(service):
    """Peringatan sumber hanya relevan untuk rumor."""
    r = service.analyze(BERITA_KUAT_POS, "berita", target="XAU")
    assert not any("tanpa sumber" in w.lower() for w in r.warnings)


def test_rumor_dengan_sumber_tidak_diberi_peringatan_sumber(service):
    r = service.analyze(RUMOR, "rumor", source="Reuters", target="XAU")
    assert r.source == "Reuters"
    assert not any("tanpa sumber" in w.lower() for w in r.warnings)


# --- ringkasan tidak mengarang -------------------------------------------

def test_ringkasan_hanya_memuat_angka_dari_hasil(service):
    r = service.analyze(BERITA_KUAT_POS, "berita", target="XAU")
    # Skor dan keyakinan di ringkasan harus sama dengan field hasil.
    assert f"{r.score:+.2f}" in r.summary
    assert f"{r.confidence:.2f}" in r.summary


def test_ringkasan_menyebut_jenis_input(service):
    b = service.analyze(BERITA_KUAT_POS, "berita", target="XAU")
    u = service.analyze(RUMOR, "rumor", target="XAU")
    assert "berita" in b.summary
    assert "rumor" in u.summary


def test_degradasi_model_dilaporkan_jujur(service):
    """Bila FOMC gagal dimuat, itu harus terlihat, bukan disembunyikan."""
    r = service.analyze(BERITA_KUAT_POS, "berita", target="XAU")
    if r.degraded:
        assert any("fomc" in d.lower() for d in r.degraded)
        assert any("gagal dimuat" in w.lower() for w in r.warnings)


# --- pemilihan model per teks --------------------------------------------
# Regresi paling berbahaya di sini: memakai satu model untuk semua input
# membuat arah terbalik, karena FOMC (stance) dan FinBERT (price) punya arti
# skor yang berlawanan.

def test_berita_emas_naik_menghasilkan_bullish(service):
    r = service.analyze(
        "Gold surged 3.2% to a record high as investors rushed into bullion.",
        "berita", target="XAU",
    )
    assert r.model_version.startswith("xau-"), f"model salah: {r.model_version}"
    assert r.score > 0
    assert r.direction == "bullish"


def test_berita_emas_turun_menghasilkan_bearish(service):
    r = service.analyze(
        "Gold plunged 4% as the dollar strengthened sharply.",
        "berita", target="XAU",
    )
    assert r.model_version.startswith("xau-")
    assert r.score < 0
    assert r.direction == "bearish"


def test_berita_fed_hawkish_berarti_emas_bearish(service):
    """Skor FOMC positif = hawkish = emas turun. Ini bukan bug."""
    r = service.analyze(
        "The Federal Reserve signalled it may raise interest rates further.",
        "berita", target="XAU",
    )
    assert r.model_version.startswith("fomc-")
    assert r.score > 0
    assert r.direction == "bearish"


def test_berita_fed_dovish_berarti_emas_bullish(service):
    r = service.analyze(
        "The Federal Reserve signalled it may cut interest rates soon.",
        "berita", target="XAU",
    )
    assert r.model_version.startswith("fomc-")
    assert r.score < 0
    assert r.direction == "bullish"


def test_dua_domain_memakai_model_berbeda(service):
    """Satu service harus bisa melayani dua domain tanpa saling mencemari."""
    emas = service.analyze(
        "Gold surged 3.2% to a record high on safe haven demand.", "berita", target="XAU"
    )
    fed = service.analyze(
        "The Federal Reserve raised interest rates by a quarter point.", "berita", target="XAU"
    )
    assert emas.model_version != fed.model_version
