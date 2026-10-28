"""Uji penjadwal preload 07:00 WIB.

Fokus pada perilaku yang mudah salah dan mahal akibatnya:
  * slot dihitung di WIB, bukan UTC (kalau salah, "07:00" jatuh pukul 14:00);
  * catch-up hanya sekali per slot (kuota eulerpool terbatas);
  * kegagalan TIDAK menandai slot selesai, supaya bisa dicoba lagi.
"""
from __future__ import annotations

from datetime import datetime

from backend.src.serve.ingest_scheduler import (
    JAKARTA,
    IngestScheduler,
    next_slot,
    slot_for,
)


def wib(*args: int) -> datetime:
    """Bangun datetime di zona WIB dengan mudah."""
    return datetime(*args, tzinfo=JAKARTA)


class Recorder:
    """Job palsu: catat slot yang dipanggil, hasilnya bisa diatur."""

    def __init__(self, results: list[bool] | None = None) -> None:
        self.slots: list[datetime] = []
        self.triggers: list[str] = []
        self._results = list(results or [])

    def __call__(self, slot: datetime, trigger: str = "schedule") -> bool:
        self.slots.append(slot)
        self.triggers.append(trigger)
        if self._results:
            return self._results.pop(0)
        return True


# --- slot_for / next_slot -------------------------------------------------

def test_slot_for_pagi_sebelum_jam_tujuh_adalah_hari_ini():
    # 05:00 WIB: slot 07:00 hari ini belum lewat.
    assert slot_for(wib(2026, 10, 26, 5, 0)) == wib(2026, 10, 26, 7, 0)


def test_slot_for_setelah_jam_tujuh_adalah_hari_ini():
    assert slot_for(wib(2026, 10, 26, 9, 30)) == wib(2026, 10, 26, 7, 0)


def test_slot_for_dihitung_di_wib_bukan_utc():
    """UTC 2026-10-26 00:30 == WIB 07:30: slot harus 26 Okt, bukan 25 Okt.

    Ini kelas bug yang sama dengan tanggal UTC di frontend: kalau slot
    dihitung di UTC, "07:00" bergeser ke 14:00 WIB.
    """
    utc_moment = datetime.fromisoformat("2026-10-26T00:30:00+00:00")
    assert slot_for(utc_moment) == wib(2026, 10, 26, 7, 0)


def test_next_slot_selalu_di_masa_depan():
    # Tepat pukul 07:00:00 -> slot berikutnya besok, bukan hari ini.
    now = wib(2026, 10, 26, 7, 0, 0)
    assert next_slot(now) == wib(2026, 10, 27, 7, 0)


def test_next_slot_dari_siang_adalah_besok_pagi():
    assert next_slot(wib(2026, 10, 26, 13, 0)) == wib(2026, 10, 27, 7, 0)


# --- catch-up -------------------------------------------------------------

def test_startup_sebelum_jam_tujuh_tidak_mengejar():
    """Aplikasi dinyalakan 05:00: belum ada yang terlewat, jangan tarik berita."""
    job = Recorder()
    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 5, 0))
    sched.tick(catch_up=True)
    assert job.slots == []


def test_startup_setelah_jam_tujuh_mengejar_sekali():
    """Dinyalakan 09:00 dengan slot 07:00 belum dijalankan -> kejar segera."""
    job = Recorder()
    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 9, 0))
    sched.tick(catch_up=True)
    assert job.slots == [wib(2026, 10, 26, 7, 0)]


def test_catch_up_tidak_diulang_untuk_slot_yang_sama():
    """Tick berulang setelah sukses tidak boleh menembak eulerpool lagi."""
    job = Recorder()
    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 9, 0))
    sched.tick(catch_up=True)
    sched.tick(catch_up=True)
    sched.tick(catch_up=True)
    assert len(job.slots) == 1


def test_kegagalan_boleh_dicoba_lagi():
    """Run gagal tidak menandai slot selesai: percobaan berikutnya mengulang."""
    job = Recorder(results=[False, True])
    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 9, 0))
    sched.tick(catch_up=True)   # gagal
    sched.tick(catch_up=True)   # dicoba lagi, sukses
    sched.tick(catch_up=True)   # sudah sukses, berhenti
    assert len(job.slots) == 2


def test_job_yang_melempar_tidak_mematikan_scheduler():
    calls = {"n": 0}

    def job(_slot, trigger="schedule"):
        calls["n"] += 1
        raise RuntimeError("API mati")

    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 9, 0))
    sched.tick(catch_up=True)
    sched.tick(catch_up=True)
    assert calls["n"] == 2  # tetap dicoba, exception tidak membocor


def test_hari_berikutnya_menjalankan_slot_baru():
    now = {"t": wib(2026, 10, 26, 9, 0)}
    job = Recorder()
    sched = IngestScheduler(job, clock=lambda: now["t"])
    sched.tick(catch_up=True)
    now["t"] = wib(2026, 10, 27, 7, 30)
    sched.tick(catch_up=True)
    assert job.slots == [wib(2026, 10, 26, 7, 0), wib(2026, 10, 27, 7, 0)]


def test_thread_start_stop_bersih():
    job = Recorder()
    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 9, 0), tick_seconds=1)
    sched.start(catch_up=True)
    sched.stop(timeout=3)
    assert len(job.slots) >= 1


# --- label trigger --------------------------------------------------------

def test_tepat_waktu_dilabeli_schedule():
    """Tick tepat pukul 07:00 dianggap run terjadwal, bukan kejar."""
    job = Recorder()
    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 7, 0, 10))
    sched.tick(catch_up=True)
    assert job.triggers == ["schedule"]


def test_startup_siang_dilabeli_catchup():
    """Dinyalakan 09:00 untuk slot 07:00 = run kejar, supaya jejak jujur."""
    job = Recorder()
    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 9, 0))
    sched.tick(catch_up=True)
    assert job.triggers == ["startup_catchup"]


# --- dedup lintas restart -------------------------------------------------

def test_restart_tidak_mengulang_slot_yang_sudah_berhasil():
    """Slot sudah ada di DB -> startup baru tidak menembak eulerpool lagi.

    Tanpa ini, setiap restart aplikasi membakar satu request eulerpool untuk
    slot yang sama.
    """
    job = Recorder()
    sched = IngestScheduler(
        job,
        clock=lambda: wib(2026, 10, 26, 16, 0),
        slot_done=lambda slot_iso: True,
    )
    sched.tick(catch_up=True)
    assert job.slots == []


def test_slot_gagal_di_db_tetap_dicoba():
    """Status gagal tidak dihitung selesai; startup berikutnya mengulang."""
    job = Recorder()
    sched = IngestScheduler(
        job,
        clock=lambda: wib(2026, 10, 26, 16, 0),
        slot_done=lambda slot_iso: False,
    )
    sched.tick(catch_up=True)
    assert len(job.slots) == 1


def test_slot_done_yang_error_tidak_menghalangi_run():
    """DB bermasalah: lebih baik mencoba tarik daripada tidak pernah jalan."""
    job = Recorder()

    def boom(_iso):
        raise RuntimeError("db rusak")

    sched = IngestScheduler(job, clock=lambda: wib(2026, 10, 26, 16, 0), slot_done=boom)
    sched.tick(catch_up=True)
    assert len(job.slots) == 1
