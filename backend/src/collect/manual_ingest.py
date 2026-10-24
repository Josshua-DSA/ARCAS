"""Ingest artikel manual dari CSV/JSON ke tabel ``raw_articles`` (FR-1).

Kanal otomatis (API + RSS) sudah jalan; modul ini menutup celah untuk input
manual: file CSV/JSON berisi berita yang dikumpulkan tangan, mis. arsip lama
untuk menguji ``clean -> score -> aggregate -> stats`` tanpa menunggu
kolektor.

Prinsip:
- Baris buruk **dilewati dengan alasan**, bukan membuat seluruh proses gagal.
  Satu tanggal rusak tidak boleh membuang 999 baris yang sehat.
- Tidak ada tebakan diam-diam: kolom wajib yang hilang adalah alasan
  pelewatan yang eksplisit, bukan nilai default karangan.
- Deduplikasi diserahkan ke ``Db.save_raw_articles`` yang sudah idempoten
  lewat (source, url) atau (source, title).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.src.schema import RawArticle

# Kolom yang wajib ada di setiap baris.
WAJIB = ("source", "title")

# Nama kolom alternatif yang lazim dipakai di file manual.
# Pemetaan ini sengaja eksplisit supaya tidak ada sihir pencocokan samar.
ALIAS: dict[str, str] = {
    "judul": "title",
    "headline": "title",
    "berita": "body",
    "isi": "body",
    "content": "body",
    "konten": "body",
    "tanggal": "published_at",
    "date": "published_at",
    "published": "published_at",
    "link": "url",
    "tautan": "url",
    "sumber": "source",
}


@dataclass
class Skip:
    """Satu baris yang dilewati, beserta alasannya."""

    baris: int  # 1-based, seperti yang dilihat manusia di editor
    alasan: str


@dataclass
class HasilIngest:
    """Ringkasan satu kali ingest."""

    dibaca: int = 0
    siap: list[RawArticle] = field(default_factory=list)
    dilewati: list[Skip] = field(default_factory=list)
    ditulis: int = 0

    @property
    def jumlah_siap(self) -> int:
        return len(self.siap)


def _parse_tanggal(nilai: Any) -> datetime | None:
    """Ubah teks tanggal jadi datetime UTC.

    Menerima ISO-8601 (termasuk sufiks ``Z``) dan format umum
    ``YYYY-MM-DD``/``DD-MM-YYYY``. Mengembalikan ``None`` bila kosong.
    Melempar ``ValueError`` bila ada isi tapi tidak bisa dibaca -- pemanggil
    yang memutuskan melewati barisnya.
    """
    if nilai is None:
        return None
    teks = str(nilai).strip()
    if not teks:
        return None
    # ``Z`` tidak diterima fromisoformat pada Python < 3.11.
    kandidat = teks.replace("Z", "+00:00") if teks.endswith("Z") else teks
    try:
        dt = datetime.fromisoformat(kandidat)
    except ValueError:
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d", "%d/%m/%Y"):
            try:
                dt = datetime.strptime(teks, fmt)
                break
            except ValueError:
                continue
        else:
            raise ValueError(f"tanggal tidak dikenali: {teks!r}") from None
    # Simpan sebagai UTC: nilai tanpa zona dianggap UTC, sesuai schema.
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_sentimen(nilai: Any) -> float | None:
    """Ubah nilai sentimen jadi float, atau ``None`` bila kosong."""
    if nilai is None:
        return None
    teks = str(nilai).strip()
    if not teks:
        return None
    try:
        return float(teks)
    except ValueError:
        raise ValueError(f"vendor_sentiment bukan angka: {teks!r}") from None


def _normalisasi_kunci(baris: dict[str, Any]) -> dict[str, Any]:
    """Petakan alias kolom ke nama baku, dan buang spasi di nama kunci."""
    hasil: dict[str, Any] = {}
    for kunci, nilai in baris.items():
        if kunci is None:
            continue
        nama = str(kunci).strip()
        if not nama:
            continue
        hasil[ALIAS.get(nama.lower(), nama)] = nilai
    return hasil


def _baris_ke_artikel(
    baris: dict[str, Any], nomor: int, fetched_at: datetime
) -> RawArticle:
    """Bangun ``RawArticle`` dari satu baris, atau ``ValueError`` bila invalid."""
    data = _normalisasi_kunci(baris)

    for kolom in WAJIB:
        nilai = data.get(kolom)
        if nilai is None or not str(nilai).strip():
            raise ValueError(f"kolom wajib '{kolom}' kosong atau tidak ada")

    title = str(data["title"]).strip()
    source = str(data["source"]).strip()

    url = data.get("url")
    url = str(url).strip() if url is not None and str(url).strip() else None
    body = data.get("body")
    body = str(body) if body is not None and str(body).strip() else None

    return RawArticle(
        source=source,
        url=url,
        title=title,
        body=body,
        published_at=_parse_tanggal(data.get("published_at")),
        fetched_at=fetched_at,
        query_target=(
            str(data["query_target"]).strip() if data.get("query_target") else None
        ),
        vendor_sentiment=_parse_sentimen(data.get("vendor_sentiment")),
    )


def _baca_csv(path: Path) -> list[dict[str, Any]]:
    """Baca CSV jadi list of dict; baris kosong dibuang."""
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        pembaca = csv.DictReader(fh)
        if pembaca.fieldnames is None:
            raise ValueError("CSV tidak punya baris header")
        return [
            dict(baris)
            for baris in pembaca
            if any((v or "").strip() for v in baris.values() if isinstance(v, str))
        ]


def _baca_json(path: Path) -> list[dict[str, Any]]:
    """Baca JSON: array of object, atau object tunggal."""
    isi = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(isi, dict):
        # Izinkan bentuk {"articles": [...]} maupun satu objek tunggal.
        for kunci in ("articles", "data", "items"):
            if isinstance(isi.get(kunci), list):
                isi = isi[kunci]
                break
        else:
            isi = [isi]
    if not isinstance(isi, list):
        raise ValueError("JSON harus array of object atau object tunggal")
    hasil = []
    for item in isi:
        if not isinstance(item, dict):
            raise ValueError(f"elemen JSON harus object, bukan {type(item).__name__}")
        hasil.append(item)
    return hasil


def baca_file(path: Path, fmt: str | None = None) -> list[dict[str, Any]]:
    """Baca file manual jadi list of dict.

    ``fmt`` eksplisit menang; selain itu ditentukan dari ekstensi.
    """
    if not path.exists():
        raise FileNotFoundError(f"File tidak ditemukan: {path}")

    format_efektif = (fmt or path.suffix.lstrip(".")).lower()
    if format_efektif == "csv":
        return _baca_csv(path)
    if format_efektif == "json":
        return _baca_json(path)
    raise ValueError(
        f"format tidak didukung: {format_efektif!r} (pakai csv atau json)"
    )


def bangun_artikel(
    baris_baris: list[dict[str, Any]],
    fetched_at: datetime | None = None,
) -> HasilIngest:
    """Validasi baris jadi ``RawArticle``; kumpulkan yang gagal beserta alasannya."""
    waktu = fetched_at or datetime.now(timezone.utc)
    hasil = HasilIngest(dibaca=len(baris_baris))

    for idx, baris in enumerate(baris_baris, start=1):
        try:
            artikel = _baris_ke_artikel(baris, idx, waktu)
        except ValueError as exc:
            hasil.dilewati.append(Skip(baris=idx, alasan=str(exc)))
            continue
        hasil.siap.append(artikel)

    return hasil
