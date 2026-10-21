"""CLI terpadu: menjalankan pipeline dari ujung ke ujung (FR-14).

Pemakaian:
    python -m backend.src.cli seed                  # isi asset_master & aliases
    python -m backend.src.cli prices --days 30      # ambil & simpan harga
    python -m backend.src.cli pipeline --limit 100  # raw -> articles -> impacts -> daily
    python -m backend.src.cli pipeline --dry-run    # lihat apa yang akan terjadi
    python -m backend.src.cli status                # isi tabel per tabel

Perintah `collect` (tarik berita) tetap di `backend.src.collect.news_cli`
supaya pemisahan tugas jelas: `news_cli` = pengumpulan, `cli` = pengolahan.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

from backend.src.pipeline import Pipeline, PipelineError
from backend.src.store.db import Database


def _print_stok(db_path: Path) -> None:
    """Cetak jumlah baris tiap tabel — untuk memastikan data benar-benar ada."""
    db = Database(db_path)
    with db.get_connection() as conn:
        tabel = [
            "raw_articles", "articles", "article_targets", "sentiments", "impacts",
            "daily_sentiment", "prices", "stat_results", "labels",
            "asset_master", "asset_aliases", "alloc_profiles",
            "alloc_suggestions", "persona_views",
        ]
        for nama in tabel:
            try:
                n = conn.execute(f"SELECT count(*) FROM {nama};").fetchone()[0]
            except Exception:  # noqa: BLE001 - tabel mungkin belum ada
                n = "—"
            tanda = "✅" if isinstance(n, int) and n > 0 else "  "
            print(f"  {tanda} {nama:<18} {n}")


def cmd_seed(args: argparse.Namespace) -> int:
    pipe = Pipeline(db_path=args.db)
    hasil = pipe.seed_universe()
    print("Universe di-seed:")
    for nama, n in hasil.items():
        print(f"  {nama:<14} {n} baris")
    return 0


def cmd_prices(args: argparse.Namespace) -> int:
    """Ambil harga nyata dan SIMPAN ke tabel prices.

    AUDIT K-5: sebelumnya PriceCollector tidak pernah menyimpan apa pun,
    sehingga tabel prices kosong dan statistik mustahil dihitung.
    """
    from backend.src.collect.yfinance_collector import PriceCollector, PriceFetchError

    end = date.today()
    start = end - timedelta(days=args.days)

    collector = PriceCollector()
    print(f"Mengambil harga {start} .. {end}")
    try:
        data = collector.fetch_universe_prices(start, end)
    except PriceFetchError as exc:
        print(f"GAGAL: {exc}")
        return 1

    db = Database(args.db)
    db.init_schema()
    total = 0
    for asset_id, records in data.items():
        for rec in records:
            db.save_price(rec)
        print(f"  {asset_id:<9} {len(records)} hari")
        total += len(records)

    if collector.last_errors:
        print("\nSebagian aset gagal (tidak diisi data palsu):")
        for asset_id, err in collector.last_errors.items():
            print(f"  {asset_id}: {err}")

    print(f"\nTotal {total} baris harga tersimpan.")
    return 0


def cmd_pipeline(args: argparse.Namespace) -> int:
    if args.dry_run:
        print("=== DRY RUN — tidak ada yang ditulis ke database ===\n")
    try:
        pipe = Pipeline(db_path=args.db, model_path=args.model)
        stats = pipe.run(limit=args.limit, dry_run=args.dry_run, seed=not args.no_seed)
    except PipelineError as exc:
        print(f"GAGAL: {exc}")
        return 1

    print(stats.ringkas())
    if stats.errors:
        print("\nContoh error:")
        for err in stats.errors[:5]:
            print(f"  - {err}")
    if args.dry_run:
        print("\n(Jalankan tanpa --dry-run untuk menyimpan.)")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    print(f"Database: {args.db}\n")
    _print_stok(Path(args.db))

    db = Database(args.db)
    print("\nUniverse aktif:")
    universe = db.get_active_universe()
    if not universe:
        print("  (kosong — jalankan: python -m backend.src.cli seed)")
    for asset in universe:
        print(f"  {asset.get('asset_id', asset)}")

    ringkas = db.get_meta_summary()
    print("\nRingkasan:")
    for key in ("articles", "sources", "days_with_news", "last_news_date", "universe_count"):
        print(f"  {key:<16} {ringkas.get(key)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="finews",
        description="FinNews — pipeline pengolahan berita ke sentimen harian.",
    )
    p.add_argument("--db", default="data/finews.db", help="path database SQLite")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("seed", help="isi asset_master & asset_aliases")
    sp.set_defaults(func=cmd_seed)

    sp = sub.add_parser("prices", help="ambil & simpan harga harian")
    sp.add_argument("--days", type=int, default=30, help="rentang hari ke belakang")
    sp.set_defaults(func=cmd_prices)

    sp = sub.add_parser("pipeline", help="jalankan alur pengolahan")
    sp.add_argument("--limit", type=int, default=100, help="maks raw_articles diproses")
    sp.add_argument("--dry-run", action="store_true", help="hitung saja, jangan tulis")
    sp.add_argument("--no-seed", action="store_true", help="jangan seed universe")
    sp.add_argument("--model", default="model/common/baseline_tfidf.joblib")
    sp.set_defaults(func=cmd_pipeline)

    sp = sub.add_parser("status", help="tampilkan isi database")
    sp.set_defaults(func=cmd_status)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
