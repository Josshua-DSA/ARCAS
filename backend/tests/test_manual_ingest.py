"""Test FR-1: ingest artikel manual dari CSV/JSON.

Kontrak yang diuji (dari context/AUDIT.md):
- kolom dipetakan ke raw_articles
- baris buruk DILEWATI dengan alasan, bukan membuat proses crash
- menjalankan ulang file yang sama tidak menggandakan baris
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from backend.src.collect.manual_ingest import (
    HasilIngest,
    baca_file,
    bangun_artikel,
)
from backend.src.store.db import Database

FETCHED = datetime(2026, 10, 10, tzinfo=timezone.utc)


# ---------------------------------------------------------------- validasi ---


def test_baris_valid_jadi_artikel() -> None:
    hasil = bangun_artikel(
        [
            {
                "source": "manual",
                "title": "Dolar naik",
                "body": "Emas tertekan",
                "published_at": "2026-10-01",
                "url": "https://x.test/1",
                "vendor_sentiment": "0.4",
            }
        ],
        fetched_at=FETCHED,
    )
    assert hasil.dibaca == 1
    assert hasil.dilewati == []
    (artikel,) = hasil.siap
    assert artikel.source == "manual"
    assert artikel.title == "Dolar naik"
    assert artikel.vendor_sentiment == pytest.approx(0.4)
    assert artikel.fetched_at == FETCHED


def test_kolom_wajib_hilang_dilewati_dengan_alasan() -> None:
    """Satu baris buruk tidak boleh membuang baris sehat lainnya."""
    hasil = bangun_artikel(
        [
            {"source": "manual", "title": "Sehat"},
            {"source": "manual"},  # title hilang
            {"title": "Tanpa source"},  # source hilang
            {"source": "  ", "title": "Source kosong"},
        ],
        fetched_at=FETCHED,
    )
    assert hasil.jumlah_siap == 1
    assert [s.baris for s in hasil.dilewati] == [2, 3, 4]
    assert all("wajib" in s.alasan for s in hasil.dilewati)


def test_tanggal_rusak_dilewati_bukan_crash() -> None:
    hasil = bangun_artikel(
        [
            {"source": "m", "title": "Ok", "published_at": "2026-10-01"},
            {"source": "m", "title": "Rusak", "published_at": "31-31-2026"},
        ],
        fetched_at=FETCHED,
    )
    assert hasil.jumlah_siap == 1
    assert len(hasil.dilewati) == 1
    assert "tanggal" in hasil.dilewati[0].alasan


def test_sentimen_bukan_angka_dilewati() -> None:
    hasil = bangun_artikel(
        [{"source": "m", "title": "X", "vendor_sentiment": "abc"}],
        fetched_at=FETCHED,
    )
    assert hasil.jumlah_siap == 0
    assert "angka" in hasil.dilewati[0].alasan


@pytest.mark.parametrize(
    ("nilai", "harapan_tahun"),
    [
        ("2026-10-01", 2026),
        ("2026-10-01T10:30:00Z", 2026),
        ("01-10-2026", 2026),
        ("2026/10/01", 2026),
    ],
)
def test_format_tanggal_diterima(nilai: str, harapan_tahun: int) -> None:
    hasil = bangun_artikel(
        [{"source": "m", "title": "X", "published_at": nilai}], fetched_at=FETCHED
    )
    assert hasil.jumlah_siap == 1
    assert hasil.siap[0].published_at is not None
    assert hasil.siap[0].published_at.year == harapan_tahun


def test_tanggal_kosong_jadi_none() -> None:
    hasil = bangun_artikel(
        [{"source": "m", "title": "X", "published_at": ""}], fetched_at=FETCHED
    )
    assert hasil.siap[0].published_at is None


def test_alias_kolom_indonesia_dipetakan() -> None:
    """Kolom 'judul'/'sumber'/'isi'/'tanggal'/'link' harus dikenali."""
    hasil = bangun_artikel(
        [
            {
                "sumber": "manual",
                "judul": "Emas cetak rekor",
                "isi": "Harga naik",
                "tanggal": "2026-10-06",
                "link": "https://x.test/7",
            }
        ],
        fetched_at=FETCHED,
    )
    assert hasil.jumlah_siap == 1
    artikel = hasil.siap[0]
    assert artikel.title == "Emas cetak rekor"
    assert artikel.body == "Harga naik"
    assert artikel.url == "https://x.test/7"


# ------------------------------------------------------------------ berkas ---


def test_baca_csv(tmp_path: Path) -> None:
    p = tmp_path / "a.csv"
    p.write_text("source,title\nmanual,Satu\nmanual,Dua\n", encoding="utf-8")
    baris = baca_file(p)
    assert len(baris) == 2
    assert baris[0]["title"] == "Satu"


def test_baca_csv_dengan_bom(tmp_path: Path) -> None:
    """Excel sering menyimpan BOM; header tidak boleh jadi '\\ufeffsource'."""
    p = tmp_path / "bom.csv"
    p.write_text("\ufeffsource,title\nmanual,Satu\n", encoding="utf-8")
    assert baca_file(p)[0]["source"] == "manual"


def test_baca_json_array(tmp_path: Path) -> None:
    p = tmp_path / "a.json"
    p.write_text(json.dumps([{"source": "m", "title": "Satu"}]), encoding="utf-8")
    assert len(baca_file(p)) == 1


def test_baca_json_objek_tunggal(tmp_path: Path) -> None:
    p = tmp_path / "satu.json"
    p.write_text(json.dumps({"source": "m", "title": "Satu"}), encoding="utf-8")
    assert len(baca_file(p)) == 1


def test_baca_json_dibungkus_articles(tmp_path: Path) -> None:
    p = tmp_path / "w.json"
    p.write_text(
        json.dumps({"articles": [{"source": "m", "title": "A"}]}), encoding="utf-8"
    )
    assert len(baca_file(p)) == 1


def test_file_tidak_ada_melempar(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        baca_file(tmp_path / "nope.csv")


def test_ekstensi_tidak_didukung(tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="tidak didukung"):
        baca_file(p)


def test_csv_tanpa_header_melempar(tmp_path: Path) -> None:
    p = tmp_path / "kosong.csv"
    p.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        baca_file(p)


# --------------------------------------------------------------- persistensi ---


def _db(tmp_path: Path) -> Database:
    db = Database(tmp_path / "t.db")
    db.init_schema()
    return db


def test_menulis_ke_raw_articles(tmp_path: Path) -> None:
    db = _db(tmp_path)
    hasil = bangun_artikel(
        [{"source": "manual", "title": "Dolar naik"}], fetched_at=FETCHED
    )
    ditulis = db.save_raw_articles([(a, None) for a in hasil.siap])
    assert ditulis == 1
    assert db.count_raw_articles() == 1


def test_ingest_ulang_tidak_menggandakan(tmp_path: Path) -> None:
    """Idempotensi: dedup lewat (source, url) atau (source, title)."""
    db = _db(tmp_path)
    baris = [{"source": "manual", "title": "Dolar naik", "url": "https://x.test/1"}]

    pertama = bangun_artikel(baris, fetched_at=FETCHED)
    assert db.save_raw_articles([(a, None) for a in pertama.siap]) == 1

    kedua = bangun_artikel(baris, fetched_at=FETCHED)
    assert db.save_raw_articles([(a, None) for a in kedua.siap]) == 0
    assert db.count_raw_articles() == 1


def test_hasil_ingest_properti() -> None:
    h = HasilIngest(dibaca=3)
    assert h.jumlah_siap == 0
