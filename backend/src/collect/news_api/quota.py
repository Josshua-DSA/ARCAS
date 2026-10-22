"""Penjaga kuota request harian — untuk sumber dengan batas 10–100 req/hari.

Mengapa modul terpisah: kuota adalah **anggaran yang harus dihormati lintas
proses**. Menyimpannya di memori saja akan hilang tiap kali CLI dipanggil
ulang, sehingga pagar 10–100/hari bisa ditembus berkali-kali dalam sehari.

Desain:
- Dihitung per (vendor, tanggal-UTC). Reset otomatis saat ganti hari.
- Persisten di tabel `api_quota_usage` pada database SQLite yang sama.
- `reserve()` bersifat atomik (UPDATE bersyarat) — dua proses bersamaan tidak
  bisa sama-sama mendapat slot terakhir.
- Default konservatif: 20 req/hari. Batas keras tidak boleh > 100.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# Pagar sesuai permintaan: jangan pernah lebih dari 100 request/hari.
HARD_CAP_PER_DAY = 100
# Default aman di tengah rentang 10–100.
DEFAULT_DAILY_BUDGET = 20
# Minimum agar sekali jalan tetap berguna (satu request = satu tarikan besar).
MIN_DAILY_BUDGET = 1


class QuotaExceeded(RuntimeError):
    """Dilempar saat anggaran request harian sudah habis."""

    def __init__(self, vendor: str, used: int, limit: int) -> None:
        self.vendor = vendor
        self.used = used
        self.limit = limit
        super().__init__(
            f"Kuota {vendor} habis: {used}/{limit} request terpakai hari ini (UTC). "
            "Kuota reset tengah malam UTC. Naikkan dengan --budget bila memang perlu, "
            f"maksimum {HARD_CAP_PER_DAY}/hari."
        )


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    """Kondisi anggaran satu vendor hari ini."""

    vendor: str
    day: str
    used: int
    limit: int

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def exhausted(self) -> bool:
        return self.remaining == 0


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS api_quota_usage (
  vendor TEXT NOT NULL,
  day    TEXT NOT NULL,          -- YYYY-MM-DD (UTC)
  used   INTEGER NOT NULL DEFAULT 0,
  limit_per_day INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (vendor, day)
);
"""


class DailyQuota:
    """Anggaran request harian yang persisten di SQLite."""

    def __init__(
        self,
        db_path: Path | str,
        vendor: str,
        limit_per_day: int = DEFAULT_DAILY_BUDGET,
    ) -> None:
        if limit_per_day < MIN_DAILY_BUDGET:
            raise ValueError(f"limit_per_day minimal {MIN_DAILY_BUDGET}")
        if limit_per_day > HARD_CAP_PER_DAY:
            raise ValueError(
                f"limit_per_day {limit_per_day} melebihi pagar keras "
                f"{HARD_CAP_PER_DAY}/hari. Batas ini disengaja."
            )
        self.db_path = Path(db_path)
        self.vendor = vendor
        self.limit_per_day = limit_per_day

    # ---------------- internals ----------------

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).date().isoformat()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute(CREATE_SQL)
        return conn

    # ---------------- public ----------------

    def status(self) -> QuotaStatus:
        """Baca pemakaian hari ini tanpa menambah apa pun."""
        day = self._today()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT used, limit_per_day FROM api_quota_usage WHERE vendor=? AND day=?;",
                (self.vendor, day),
            ).fetchone()
        used = row[0] if row else 0
        limit = self.limit_per_day
        return QuotaStatus(vendor=self.vendor, day=day, used=used, limit=limit)

    def reserve(self, n: int = 1) -> QuotaStatus:
        """Pesan `n` slot request. Melempar `QuotaExceeded` bila tidak cukup.

        Atomik: UPDATE bersyarat `used + n <= limit`, jadi dua proses tidak
        bisa melewati batas bersama-sama.
        """
        if n < 1:
            raise ValueError("n minimal 1")
        day = self._today()
        limit = self.limit_per_day
        now = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE;")
            conn.execute(
                """
                INSERT INTO api_quota_usage (vendor, day, used, limit_per_day, updated_at)
                VALUES (?, ?, 0, ?, ?)
                ON CONFLICT(vendor, day) DO UPDATE SET limit_per_day=excluded.limit_per_day;
                """,
                (self.vendor, day, limit, now),
            )
            cur = conn.execute(
                """
                UPDATE api_quota_usage
                   SET used = used + ?, updated_at = ?
                 WHERE vendor = ? AND day = ? AND used + ? <= ?;
                """,
                (n, now, self.vendor, day, n, limit),
            )
            if cur.rowcount == 0:
                used = conn.execute(
                    "SELECT used FROM api_quota_usage WHERE vendor=? AND day=?;",
                    (self.vendor, day),
                ).fetchone()[0]
                conn.execute("ROLLBACK;")
                raise QuotaExceeded(self.vendor, used + n, limit)

            row = conn.execute(
                "SELECT used FROM api_quota_usage WHERE vendor=? AND day=?;",
                (self.vendor, day),
            ).fetchone()
            conn.execute("COMMIT;")

        return QuotaStatus(vendor=self.vendor, day=day, used=row[0], limit=limit)

    def refund(self, n: int = 1) -> None:
        """Kembalikan slot bila request ternyata gagal sebelum terkirim.

        Dipakai saat exception jaringan terjadi sebelum server menerima request,
        supaya kegagalan lokal tidak memakan anggaran.
        """
        day = self._today()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE api_quota_usage
                   SET used = MAX(0, used - ?), updated_at = ?
                 WHERE vendor = ? AND day = ?;
                """,
                (n, datetime.now(timezone.utc).isoformat(), self.vendor, day),
            )
