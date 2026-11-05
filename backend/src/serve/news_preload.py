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

# Seberapa jauh ke belakang harga ditarik ulang. Sepuluh hari menutup akhir
# pekan panjang dan libur bursa; `save_price` memakai INSERT OR REPLACE
# sehingga mengulang rentang yang sama tidak menggandakan baris.
PRICE_LOOKBACK_DAYS = 10


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


def _refresh_prices(db_path: Path, days: int = PRICE_LOOKBACK_DAYS) -> tuple[int, str]:
    """Tarik harga harian terbaru dan simpan ke tabel `prices`.

    Kenapa di sini: `Pipeline.run()` hanya menjalankan
    clean -> score -> aggregate -> compute_stats, **tanpa** mengambil harga.
    Tanpa langkah ini `daily_sentiment` bergerak sampai hari ini sementara
    `prices` berhenti di hari bursa terakhir yang pernah ditarik manual,
    sehingga `/api/series` mengembalikan dua ujung tanggal yang berbeda dan
    grafik tampak "tidak sampai hari ini".

    Kegagalan Yahoo tidak boleh menggagalkan preload berita: harga adalah
    pelengkap, berita adalah inti job. Pemanggil mencatat pesannya saja.
    """
    from datetime import date, timedelta

    from backend.src.collect.yfinance_collector import PriceCollector, PriceFetchError
    from backend.src.store.db import Database

    end = date.today()
    start = end - timedelta(days=days)
    collector = PriceCollector()
    try:
        data = collector.fetch_universe_prices(start, end)
    except PriceFetchError as exc:
        return 0, f"harga gagal: {exc}"

    db = Database(db_path)
    total = 0
    for records in data.values():
        for rec in records:
            db.save_price(rec)
            total += 1

    catatan = f"harga: {total} baris"
    if collector.last_errors:
        catatan += f" (gagal: {', '.join(collector.last_errors)})"
    return total, catatan


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

    run_id = db.claim_ingest_slot(trigger, scheduled_for=slot.isoformat())
    if run_id is None:
        # Proses lain sudah memegang slot ini. JANGAN menembak eulerpool:
        # itulah inti perbaikan P1-8 -- kuota harian tidak boleh terbakar dua
        # kali hanya karena ada dua worker atau proses lama yang belum mati.
        LOGGER.info(
            "Slot %s sudah diklaim proses lain; preload dilewati.", slot.isoformat()
        )
        return True  # slot dianggap tertangani, bukan gagal
    raw_new = 0
    catatan: list[str] = []

    try:
        raw_new, note = _collect_via_eulerpool(db_file)
        catatan.append(note)
    except Exception as exc:  # noqa: BLE001 - penarikan gagal tidak fatal
        catatan.append(f"penarikan gagal: {exc}")
        db.finish_ingest_run(run_id, "failed", raw_new=0, detail="; ".join(catatan))
        return False

    # Harga ditarik SEBELUM pipeline: `aggregate` dan `compute_stats` membaca
    # `prices`, jadi urutan ini penting. Kegagalannya tidak fatal.
    try:
        _, note_harga = _refresh_prices(db_file)
        catatan.append(note_harga)
    except Exception as exc:  # noqa: BLE001 - harga pelengkap, bukan inti job
        catatan.append(f"harga gagal: {exc}")

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
