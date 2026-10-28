"""Penjadwal preload berita harian pukul 07:00 WIB.

Kenapa modul ini ada
--------------------
Sebelumnya berita hanya masuk bila seseorang menjalankan CLI secara manual,
sehingga halaman menampilkan data lama (atau kosong) sampai ada yang ingat.
Modul ini menjalankan rantai penuh sekali sehari:

    eulerpool -> raw_articles -> clean -> articles -> score -> impacts

Tiga keputusan desain yang penting:

1. **Zona waktu WIB, bukan UTC.** Slot dihitung di `Asia/Jakarta`. Bila
   dihitung di UTC, "07:00" akan jatuh pukul 14:00 WIB -- kesalahan yang
   sama jenisnya dengan bug tanggal UTC di frontend.

2. **Catch-up saat startup.** Bila aplikasi mati semalaman (atau dinyalakan
   pukul 09:00), slot 07:00 hari ini terlewat. Saat start, scheduler
   memeriksa apakah `ingest_runs` sudah punya run sukses untuk slot hari ini;
   bila belum, ia menjalankan satu run "kejar" segera. Tanpa ini, pengguna
   yang menyalakan aplikasi siang hari tetap melihat berita kemarin.

3. **Satu run per slot.** `scheduled_for` disimpan di `ingest_runs` sehingga
   restart berulang tidak memicu tarikan berulang (penting karena eulerpool
   punya kuota harian). Kegagalan tidak dihitung sebagai "sudah jalan":
   run `failed` boleh dicoba lagi pada startup berikutnya.

Scheduler sengaja memakai thread latar + loop tidur, bukan APScheduler, agar
tidak menambah dependensi baru pada proyek yang sudah punya jadwal sederhana.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable
from zoneinfo import ZoneInfo

LOGGER = logging.getLogger(__name__)

JAKARTA = ZoneInfo("Asia/Jakarta")

# Slot harian: 07:00 WIB.
RUN_HOUR = 7
RUN_MINUTE = 0

# Seberapa sering loop bangun untuk memeriksa jam. 30 detik cukup presisi
# untuk jadwal harian dan tidak membebani apa pun.
TICK_SECONDS = 30


def slot_for(moment: datetime) -> datetime:
    """Slot 07:00 WIB yang berlaku untuk `moment` (zona waktu apa pun).

    Bila `moment` sebelum 07:00, slot yang berlaku adalah 07:00 hari itu juga
    -- run pagi belum lewat, jadi startup pukul 05:00 tidak perlu mengejar
    apa pun sampai jam 07:00 tiba.
    """
    local = moment.astimezone(JAKARTA)
    return local.replace(hour=RUN_HOUR, minute=RUN_MINUTE, second=0, microsecond=0)


def next_slot(now: datetime) -> datetime:
    """Slot 07:00 WIB berikutnya yang masih di masa depan."""
    candidate = slot_for(now)
    if candidate <= now.astimezone(JAKARTA):
        candidate += timedelta(days=1)
    return candidate


class IngestScheduler:
    """Menjalankan `job` sekali sehari pada 07:00 WIB, plus catch-up startup.

    `job` menerima satu argumen: slot (datetime berzona WIB) yang diwakili
    run tersebut, dan mengembalikan True bila berhasil. Scheduler tidak tahu
    isi pekerjaannya -- itu urusan `news_preload.py`.
    """

    def __init__(
        self,
        job: Callable[..., bool],
        *,
        clock: Callable[[], datetime] | None = None,
        tick_seconds: int = TICK_SECONDS,
        slot_done: Callable[[str], bool] | None = None,
    ) -> None:
        self._job = job
        self._clock = clock or (lambda: datetime.now(tz=JAKARTA))
        self._tick_seconds = tick_seconds
        # `slot_done` dibaca dari DB (ingest_runs) agar restart aplikasi tidak
        # mengulang tarikan untuk slot yang sudah berhasil.
        self._slot_done = slot_done
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_ok_slot: datetime | None = None

    # -- API publik ------------------------------------------------------
    def start(self, *, catch_up: bool = True) -> None:
        """Nyalakan thread latar. Idempoten: panggilan kedua diabaikan."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, kwargs={"catch_up": catch_up},
            name="arcas-ingest-scheduler", daemon=True,
        )
        self._thread.start()
        LOGGER.info("Scheduler preload aktif; slot harian %02d:%02d WIB",
                    RUN_HOUR, RUN_MINUTE)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=timeout)

    def tick(self, *, catch_up: bool = True) -> None:
        """Satu langkah pemeriksaan, dipisah agar bisa diuji tanpa thread."""
        now = self._clock()
        due = slot_for(now)
        if catch_up:
            # Kejar slot yang belum pernah sukses (termasuk hari ini bila
            # sudah lewat 07:00 tapi run belum ada).
            if self._last_ok_slot is None or due > self._last_ok_slot:
                if self._should_run(due, now):
                    lokal = now.astimezone(JAKARTA)
                    # Terlambat lebih dari semenit dianggap run "kejar", bukan
                    # run terjadwal -- supaya jejak di ingest_runs jujur.
                    trigger = "schedule" if (lokal - due) < timedelta(minutes=1) else "startup_catchup"
                    self._run(due, trigger=trigger)
            return
        # Tanpa catch-up: hanya tepat saat slot tiba.
        if now.astimezone(JAKARTA) >= due and self._last_ok_slot != due:
            self._run(due, trigger="schedule")

    # -- internal --------------------------------------------------------
    def _should_run(self, due: datetime, now: datetime) -> bool:
        """Jalankan bila slot sudah tiba dan belum ada run sukses untuk slot itu.

        `due` boleh di masa depan (startup pukul 05:00): saat itu tidak ada
        yang perlu dikejar, cukup tunggu.
        """
        local_now = now.astimezone(JAKARTA)
        if local_now < due:
            return False
        if self._last_ok_slot == due:
            return False
        # Cek DB: restart aplikasi tidak boleh mengulang tarikan slot yang
        # sudah berhasil (kuota eulerpool terbatas).
        if self._slot_done is not None:
            try:
                if self._slot_done(due.isoformat()):
                    self._last_ok_slot = due
                    return False
            except Exception:  # noqa: BLE001 - DB bermasalah != jangan jalan
                LOGGER.exception("Gagal memeriksa status slot %s", due.isoformat())
        return True

    def _run(self, slot: datetime, *, trigger: str = "schedule") -> None:
        try:
            ok = bool(self._job(slot, trigger=trigger))
        except Exception:  # noqa: BLE001 - job tidak boleh mematikan thread
            LOGGER.exception("Preload berita gagal untuk slot %s", slot.isoformat())
            return
        if ok:
            self._last_ok_slot = slot
            LOGGER.info("Preload berita selesai untuk slot %s", slot.isoformat())
        else:
            # Jangan tandai slot selesai: percobaan berikutnya boleh mengulang.
            LOGGER.warning("Preload berita tidak tuntas untuk slot %s; akan dicoba lagi",
                           slot.isoformat())

    def _loop(self, *, catch_up: bool) -> None:
        while not self._stop.is_set():
            try:
                self.tick(catch_up=catch_up)
            except Exception:  # noqa: BLE001 - loop harus tetap hidup
                LOGGER.exception("Kesalahan pada loop scheduler preload")
            self._stop.wait(self._tick_seconds)


def seconds_until(target: datetime, now: datetime | None = None) -> float:
    """Sisa detik sampai `target`; dipakai saat startup untuk log."""
    ref = now or datetime.now(tz=JAKARTA)
    return max(0.0, (target - ref.astimezone(JAKARTA)).total_seconds())


def default_db_path() -> Path:
    return Path("data/finews.db")


__all__ = [
    "IngestScheduler",
    "JAKARTA",
    "RUN_HOUR",
    "RUN_MINUTE",
    "next_slot",
    "seconds_until",
    "slot_for",
]
