"""Uji gerbang input: hanya berita/rumor yang boleh lolos.

Kasus uji diambil dari kekhawatiran nyata: "halo" dan "besok emas naik nggak?"
tidak boleh menghasilkan analisis apa pun.
"""
from __future__ import annotations

import pytest

from backend.src.serve.sim_input import (
    InputKind,
    InputRejected,
    confidence_penalty,
    validate,
)

BERITA_EMAS = ("Gold steadies as the dollar retreats from a two-week high, "
               "with traders watching the Federal Reserve for signals.")
BERITA_FED = ("Fed officials signalled patience on further easing, according to "
              "minutes released on Wednesday.")
RUMOR_XAU = ("Kabarnya ada bank sentral besar yang menambah cadangan emas bulan ini, "
             "menurut sumber yang enggan disebut namanya.")


def test_berita_sah_lolos():
    v = validate(BERITA_EMAS, "berita")
    assert v.kind is InputKind.NEWS
    assert v.is_rumor is False
    assert v.text.startswith("Gold steadies")


def test_rumor_sah_lolos_dan_ditandai():
    v = validate(RUMOR_XAU, "rumor")
    assert v.kind is InputKind.RUMOR
    assert v.is_rumor is True
    assert v.had_rumor_cues is True


# --- penolakan: kasus yang diminta pengguna -------------------------------

@pytest.mark.parametrize("teks", [
    "halo",
    "halo apa kabar",
    "terima kasih",
    "p",
    "tes tes tes",
    "siang",
])
def test_obrolan_ditolak(teks):
    with pytest.raises(InputRejected) as exc:
        validate(teks, "berita")
    assert exc.value.code in ("terlalu_pendek", "obrolan")


@pytest.mark.parametrize("teks", [
    "Besok emas naik nggak?",
    "Menurutmu harga emas akan naik?",
    "Apakah Fed akan memangkas suku bunga tahun ini?",
    "Bagaimana prospek XAU minggu depan?",
    "Should I buy gold now?",
    "What do you think about SPX next month?",
])
def test_pertanyaan_ditolak(teks):
    with pytest.raises(InputRejected) as exc:
        validate(teks, "berita")
    assert exc.value.code in ("pertanyaan", "terlalu_pendek")


def test_pertanyaan_panjang_ditolak_bukan_diproses():
    """Pertanyaan berkalimat lengkap tetap ditolak, bukan dijawab."""
    teks = ("Menurut Anda, apakah harga emas akan terus naik setelah Fed "
            "memangkas suku bunga bulan lalu? Saya ingin tahu pendapat Anda.")
    with pytest.raises(InputRejected) as exc:
        validate(teks, "berita")
    assert exc.value.code == "pertanyaan"


def test_teks_ensiklopedis_ditolak_bila_tanpa_penanda_pasar():
    """Teks definisi murni (tanpa penanda pasar) tetap ditolak.

    Catatan: kalimat ensiklopedis yang memuat kata "emas"/"pasar" akan lolos,
    dan itu disengaja. Membedakan "Emas adalah logam mulia..." dari satu berita
    pendek sulit dilakukan tanpa LLM; menolak berita asli jauh lebih merugikan
    daripada meloloskan satu kalimat definisi.
    """
    teks = "Fotosintesis adalah proses tumbuhan mengubah cahaya menjadi energi kimia."
    with pytest.raises(InputRejected) as exc:
        validate(teks, "berita")
    assert exc.value.code == "bukan_laporan"


def test_terlalu_pendek():
    with pytest.raises(InputRejected) as exc:
        validate("Emas naik.", "berita")
    assert exc.value.code == "terlalu_pendek"


def test_terlalu_panjang():
    with pytest.raises(InputRejected) as exc:
        validate("Gold rose. " * 500, "berita")
    assert exc.value.code == "terlalu_panjang"


def test_jenis_tidak_dikenal():
    with pytest.raises(InputRejected) as exc:
        validate(BERITA_EMAS, "opini")
    assert exc.value.code == "jenis_tidak_dikenal"


# --- penurunan keyakinan untuk rumor -------------------------------------

def test_rumor_menurunkan_keyakinan():
    v = validate(RUMOR_XAU, "rumor")
    assert confidence_penalty(v) == 0.60


def test_berita_biasa_tanpa_penalti():
    v = validate(BERITA_FED, "berita")
    assert confidence_penalty(v) == 1.0


def test_berita_yang_memuat_penanda_rumor_diturunkan_sebagian():
    v = validate("Gold reportedly rose after unconfirmed talk of central bank buying, "
                 "people familiar with the matter said.", "berita")
    assert v.had_rumor_cues is True
    assert confidence_penalty(v) == 0.85


# --- pesan penolakan berguna ---------------------------------------------

def test_penolakan_menyertakan_contoh_format():
    with pytest.raises(InputRejected) as exc:
        validate("halo", "berita")
    assert len(exc.value.contoh) >= 2
    assert any("Gold" in c or "Fed" in c or "IMF" in c for c in exc.value.contoh)


def test_pesan_penolakan_berbahasa_indonesia_dan_spesifik():
    with pytest.raises(InputRejected) as exc:
        validate("Besok emas naik nggak?", "berita")
    assert "pertanyaan" in exc.value.message.lower()
    assert "berita" in exc.value.message.lower()


# --- regresi: gerbang tidak boleh menolak berita sungguhan ----------------

def test_judul_berita_yang_berbentuk_tanya_tetap_diterima():
    """Judul bertanya adalah gaya penulisan berita, bukan pertanyaan pengguna.

    Versi pertama gerbang ini menolak "Gold Under Pressure: Is a Trend
    Reversal Near?" -- padahal itu judul asli di basis data.
    """
    v = validate("Gold Under Pressure: Is a Trend Reversal Near? Analysts "
                 "point to $4,120 support as the next level to watch.", "berita")
    assert v.kind is InputKind.NEWS


def test_judul_dengan_tanda_tanya_di_tengah_tetap_diterima():
    v = validate("Obsessed with CoreWeave and the AI trade? You're missing out "
                 "on some great opportunities elsewhere in the market.", "berita")
    assert v.kind is InputKind.NEWS


def test_berita_tanpa_badan_hanya_judul_tetap_diterima():
    """Banyak artikel di DB hanya berisi judul; bukan alasan untuk menolak."""
    v = validate("Gold falls near $4,120 as Iran peace uncertainty, Fed rate "
                 "risks weigh on bullion", "berita")
    assert v.kind is InputKind.NEWS


def test_seluruh_berita_di_basis_data_diterima():
    """Penjaga terpenting: gerbang tidak boleh menolak berita yang sudah sah.

    Menolak obrolan itu murah; menolak berita asli berarti halaman tidak bisa
    dipakai sama sekali untuk data yang sudah dimiliki.
    """
    from pathlib import Path
    from backend.src.store.db import Database

    db_file = Path("data/finews.db")
    if not db_file.exists():
        pytest.skip("basis data tidak tersedia")
    db = Database(db_file)
    with db.get_connection() as conn:
        rows = conn.execute("SELECT title, COALESCE(body,'') FROM articles").fetchall()
    if not rows:
        pytest.skip("belum ada artikel")

    ditolak = []
    for title, body in rows:
        try:
            validate((title + ". " + body).strip(), "berita")
        except InputRejected as exc:
            ditolak.append((exc.code, title[:60]))
    assert not ditolak, f"gerbang menolak berita asli: {ditolak[:5]}"
