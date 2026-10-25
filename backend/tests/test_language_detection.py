"""Test deteksi bahasa EN/ID (backend/src/normalize/cleaner.py).

Latar belakang: pipeline melewati artikel non-Inggris sebelum scoring karena
terjemahan ID->EN MATI 2026-10-11 dan kedua model spesialis hanya dilatih
pada teks Inggris. Konsekuensinya, salah klasifikasi bahasa kini berarti
berita sah ikut terbuang — bukan sekadar label yang salah.

Heuristik kata fungsi lama menandai headline emas pendek sebagai `other`
("Gold rallies as Fed signals rate cuts ahead" tidak memuat satu pun penanda
Inggris), sehingga test ini menjaga agar detektor tetap benar untuk kalimat
pendek tanpa kata fungsi umum.
"""

from __future__ import annotations

import pytest

from backend.src.normalize.cleaner import ArticleCleaner
from backend.src.schema import Lang

# Headline nyata yang panjangnya pendek dan miskin kata fungsi. Semua ini
# adalah teks Inggris yang sah dan WAJIB lolos ke scoring.
HEADLINE_INGGRIS = [
    "Gold rallies as Fed signals rate cuts ahead",
    "Gold falls sharply as dollar strengthens",
    "Gold price jumps as investors seek safe haven",
    "Gold hits record high",
    "Fed holds rates steady",
    "S&P 500 closes at record high on tech rally",
    "Local weather forecast for Jakarta tomorrow",
    "Dollar weakens, bullion climbs",
]

BERITA_INDONESIA = [
    "Harga emas melonjak ke rekor tertinggi hari ini",
    "Harga emas anjlok tajam setelah bank sentral menaikkan suku bunga",
    "Harga emas stabil pada perdagangan hari ini",
    "Saham emiten tambang naik karena rupiah melemah",
    "Investor asing menarik dana dari pasar obligasi",
]


@pytest.mark.parametrize("judul", HEADLINE_INGGRIS)
def test_headline_inggris_pendek_dikenali_en(judul: str) -> None:
    """Headline Inggris pendek tidak boleh jatuh ke `other`."""
    assert ArticleCleaner.detect_language(judul, "") is Lang.EN


@pytest.mark.parametrize("judul", BERITA_INDONESIA)
def test_berita_indonesia_dikenali_id(judul: str) -> None:
    assert ArticleCleaner.detect_language(judul, "") is Lang.ID


def test_en_dominan_walau_body_pendek() -> None:
    """Judul + body Inggris tetap EN, bukan OTHER."""
    hasil = ArticleCleaner.detect_language(
        "Gold surges to record high",
        "Bullion gained as the dollar weakened against major currencies.",
    )
    assert hasil is Lang.EN


def test_teks_kosong_tetap_other() -> None:
    """Tanpa teks, tidak ada dasar menebak bahasa."""
    assert ArticleCleaner.detect_language("", None) is Lang.OTHER
    assert ArticleCleaner.detect_language("", "   ") is Lang.OTHER


def test_heuristic_fallback_masih_ada() -> None:
    """Cadangan tanpa lingua harus tetap bisa dipanggil.

    Lingkungan yang tidak memasang `lingua-language-detector` memakai jalur
    ini; ia tidak seakurat lingua tetapi tidak boleh melempar exception.
    Penanda dicocokkan dengan spasi di kedua sisi, jadi kalimat uji harus
    memuat kata fungsi yang berdiri sendiri (" yang ", " dan ", dst).
    """
    assert ArticleCleaner._detect_language_heuristic("harga emas naik dan saham turun") is Lang.ID
    assert ArticleCleaner._detect_language_heuristic("gold price rises and stock market falls") is Lang.EN


def test_detektor_dibangun_sekali(caplog: pytest.LogCaptureFixture) -> None:
    """Detektor lingua di-cache, bukan dibangun ulang per artikel.

    Membangun detektor butuh ~100 ms; membangunnya per artikel akan
    memperlambat ingest secara nyata.
    """
    pertama = ArticleCleaner._get_lingua_detector()
    kedua = ArticleCleaner._get_lingua_detector()
    assert pertama is kedua
