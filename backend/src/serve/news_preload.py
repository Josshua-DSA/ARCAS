"""Job preload berita: satu tarikan terjadwal -> rantai penuh sampai `impacts`.

Rantai yang dijalankan (dan alasannya)
--------------------------------------
GUI membaca tabel `impacts`. Berita yang hanya masuk ke `raw_articles` TIDAK
pernah muncul di halaman. Karena itu job ini tidak berhenti di penarikan:

    eulerpool -> raw_articles -> [clean] -> articles -> [score] -> impacts
                                                       -> [aggregate] -> daily_sentiment

Setiap tahap dicatat ke `ingest_runs` supaya kegagalan sebagian terlihat
sebagai `partial`, bukan diam-diam dianggap sukses.

Kuota
-----
`EulerpoolAdapter` dibungkus `DailyQuota` (lihat news_cli). Job ini memakai
1 request per run. Karena scheduler menjalankan sekali sehari per slot, kuota
aman; bila kuota habis job mencatat `failed` dengan alasan jelas dan tidak
melempar exception ke thread scheduler.
"""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

DEFAULT_MODEL = "model/common/baseline_tfidf.joblib"


def _collect_via_eulerpool(db_path: Path) -> tuple[int, str]:
    """Tarik berita eulerpool dan simpan ke raw_articles.

    Mengembalikan (jumlah_baris_baru, catatan). Meniru `news_cli eulerpool`
    tetapi tanpa print, agar bisa dipanggil dari proses server.
    """
    from backend.src.collect.news_api.base import ApiStatus
    from backend.src.collect.news_api.eulerpool import EulerpoolAdapter
    from backend.src.collect.news_api.quota import (
        DEFAULT_DAILY_BUDGET,
        DailyQuota,
    )
    from backend.src.store.db import Database

    db = Database(db_path)
    quota = DailyQuota(str(db_path), "eulerpool", limit_per_day=DEFAULT_DAILY_BUDGET)
    status = quota.status()
    if status.remaining < 1:
        return 0, f"kuota eulerpool habis ({status.used}/{status.limit})"

    adapter = EulerpoolAdapter(quota=quota)
    report = adapter.probe()
    if report.status is not ApiStatus.OK:
        return 0, f"probe eulerpool gagal: {report.status} {report.detail}"

    hasil = adapter.fetch_all()
    jumlah = sum(len(items) for items in hasil.values())
    if not jumlah:
        return 0, "eulerpool tidak mengembalikan berita"

    # Simpan seluruh item (bukan per target) supaya satu berita tidak
    # terduplikasi ketika relevan untuk beberapa target.
    rows = []
    fetched_at = datetime.now().astimezone()
    for items in hasil.values():
        for item in items:
            rows.append((item.to_raw_article(fetched_at), item.payload or None))
    inserted = db.save_raw_articles(rows)
    return inserted, f"eulerpool: {jumlah} item, {inserted} baru"


def _run_pipeline(db_path: Path, model_path: str, limit: int) -> tuple[bool, str, dict[str, int]]:
    """Jalankan clean -> score -> aggregate lewat Pipeline yang sudah ada."""
    from backend.src.pipeline import Pipeline, PipelineError

    try:
        pipe = Pipeline(db_path=str(db_path), model_path=model_path)
        stats = pipe.run(limit=limit, dry_run=False, seed=True)
    except PipelineError as exc:
        return False, f"pipeline gagal: {exc}", {}
    except Exception as exc:  # noqa: BLE001 - laporkan, jangan matikan scheduler
        return False, f"pipeline error: {exc}", {}

    metrik = {
        "articles_clean": int(getattr(stats, "artikel_tertulis", 0) or 0),
        "impacts_new": int(getattr(stats, "impact_tertulis", 0) or 0),
    }
    # ringkas() berisi newline; untuk kolom detail kita ratakan jadi satu baris.
    ringkas = " | ".join(
        baris.strip() for baris in (stats.ringkas() or "").splitlines() if baris.strip()
    )
    return True, ringkas, metrik


def run_preload(
    slot: datetime,
    *,
    db_path: Path | str = "data/finews.db",
    model_path: str = DEFAULT_MODEL,
    limit: int = 100,
    trigger: str = "schedule",
) -> bool:
    """Satu siklus preload untuk `slot`. True bila setidaknya penarikan berhasil.

    Nilai kembali sengaja boolean: scheduler hanya perlu tahu apakah slot ini
    boleh dianggap selesai. Rincian tersimpan di tabel `ingest_runs`.
    """
    from backend.src.store.db import Database

    db_file = Path(db_path)
    db = Database(db_file)
    db.init_schema()

    run_id = db.start_ingest_run(trigger, scheduled_for=slot.isoformat())
    raw_new = 0
    catatan: list[str] = []

    try:
        raw_new, note = _collect_via_eulerpool(db_file)
        catatan.append(note)
    except Exception as exc:  # noqa: BLE001 - penarikan gagal tidak fatal
        catatan.append(f"penarikan gagal: {exc}")
        db.finish_ingest_run(run_id, "failed", raw_new=0, detail="; ".join(catatan))
        return False

    # Tidak ada berita baru bukan kegagalan: mungkin memang belum ada kabar
    # baru. Tetap jalankan pipeline supaya artikel lama yang belum diskor
    # ikut terproses.
    ok, ringkas, metrik = _run_pipeline(db_file, model_path, limit)
    catatan.append(ringkas)

    if ok:
        # Semua tahap berjalan. Bedakan "ada berita baru" dari "tidak ada
        # berita baru" -- yang kedua bukan kegagalan, tetapi bukan pula
        # tarikan yang membawa data baru.
        status = "ok" if raw_new > 0 else "no_new"
    else:
        status = "partial" if raw_new > 0 else "failed"

    db.finish_ingest_run(
        run_id, status, raw_new=raw_new,
        articles_clean=metrik.get("articles_clean", 0),
        impacts_new=metrik.get("impacts_new", 0),
        detail="; ".join(catatan)[:2000],
    )
    LOGGER.info("Preload slot %s selesai: %s (%s)", slot.isoformat(), status,
                "; ".join(catatan)[:300])
    # 'no_new' HARUS dianggap sukses: kalau tidak, scheduler menganggap slot
    # gagal dan mencoba ulang setiap tick -- menghabiskan kuota eulerpool.
    return status in ("ok", "no_new", "partial")


def make_job(**kwargs: Any):
    """Buat callable (slot, trigger) -> bool untuk IngestScheduler."""
    def _job(slot: datetime, trigger: str = "schedule") -> bool:
        return run_preload(slot, trigger=trigger, **kwargs)
    return _job
