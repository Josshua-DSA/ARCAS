"""CLI: identifikasi API berita & tarik berita real-time ke database.

Pemakaian:
    python -m backend.src.collect.news_cli identify
    python -m backend.src.collect.news_cli health
    python -m backend.src.collect.news_cli fetch --target XAU --limit 20
    python -m backend.src.collect.news_cli fetch --target all --dry-run

Lingkup terkunci: XAU, RATE_UST, SPX.
"""

from __future__ import annotations

import argparse
import json
import sys

from backend.src.collect.news_api import ApiRegistry, utcnow
from backend.src.collect.news_api.base import LOCKED_TARGETS, NewsItem
from backend.src.collect.rss_collector import RSSCollector
from backend.src.store.db import Database


def _print_health(registry: ApiRegistry, include_rss: bool = True) -> None:
    print("=== IDENTIFIKASI API BERITA ===")
    print(f"{'penyedia':<26} {'status':<14} {'usable':<7} {'n':<5} detail")
    print("-" * 96)
    for report in registry.health(probe=True):
        d = report.as_dict()
        print(
            f"{d['provider']:<26} {d['status']:<14} {str(d['usable']):<7} "
            f"{d['sample_size']:<5} {(d['detail'] or '')[:38]}"
        )

    if include_rss:
        print("\n=== FEED RSS ===")
        rss = RSSCollector()
        for status in rss.health():
            print(
                f"{'rss:' + status.name:<26} {status.status.value:<14} "
                f"{str(status.status.value == 'ok'):<7} {status.item_count:<5} {status.detail[:38]}"
            )


def _dedupe(items: list[NewsItem]) -> list[NewsItem]:
    """Buang duplikat lintas penyedia berdasarkan judul ternormalisasi."""
    seen: set[str] = set()
    out: list[NewsItem] = []
    for item in items:
        key = " ".join(item.title.lower().split())[:120]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _collect(target: str, limit: int, use_api: bool, use_rss: bool) -> list[NewsItem]:
    """Kumpulkan berita dari semua sumber yang tersedia untuk satu target."""
    items: list[NewsItem] = []

    if use_api:
        registry = ApiRegistry()
        for name in registry.usable():
            try:
                items.extend(registry.get(name).fetch(target, limit=limit))
            except Exception as exc:  # noqa: BLE001 - satu penyedia gagal tidak fatal
                print(f"  ! {name} gagal: {type(exc).__name__}: {exc}", file=sys.stderr)

    if use_rss:
        try:
            items.extend(RSSCollector().fetch(target, limit=limit))
        except Exception as exc:  # noqa: BLE001
            print(f"  ! rss gagal: {exc}", file=sys.stderr)

    return _dedupe(items)[:limit]


def cmd_identify(_args: argparse.Namespace) -> int:
    _print_health(ApiRegistry())
    return 0


def cmd_health(args: argparse.Namespace) -> int:
    registry = ApiRegistry()
    payload = {
        "generated_at": utcnow().isoformat(),
        "apis": [r.as_dict() for r in registry.health(probe=True)],
        "rss": [
            {
                "feed": s.name,
                "status": s.status.value,
                "items": s.item_count,
                "detail": s.detail,
            }
            for s in RSSCollector().health()
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_health(registry)
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    targets = list(LOCKED_TARGETS) if args.target == "all" else [args.target]
    db = Database(args.db)
    db.init_schema()  # idempoten: CREATE TABLE IF NOT EXISTS

    total_new = 0
    for target in targets:
        print(f"\n=== {target} ===")
        items = _collect(target, args.limit, use_api=not args.rss_only, use_rss=not args.api_only)
        print(f"  {len(items)} berita unik")
        for item in items[: args.show]:
            ts = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else "?"
            print(f"    [{ts}] {item.source:<32} {item.title[:58]}")

        if args.dry_run or not items:
            continue

        fetched_at = utcnow()
        rows: list[tuple] = [
            (item.to_raw_article(fetched_at), item.payload or None) for item in items
        ]
        inserted = db.save_raw_articles(rows)
        total_new += inserted
        print(f"  tersimpan: {inserted} baru dari {len(rows)}")

    if not args.dry_run:
        print(f"\nTotal baru di raw_articles: {total_new} (db: {db.db_path})")
    return 0



def cmd_eulerpool(args: argparse.Namespace) -> int:
    """Tarik berita pasar Eulerpool dengan pagar kuota harian.

    Satu request melayani ketiga target, jadi perintah ini sengaja tidak
    memakai loop per-target seperti `fetch`.
    """
    from backend.src.collect.news_api.base import ApiStatus
    from backend.src.collect.news_api.eulerpool import EulerpoolAdapter
    from backend.src.collect.news_api.quota import (
        DEFAULT_DAILY_BUDGET,
        DailyQuota,
        QuotaExceeded,
    )

    db = Database(args.db)
    db.init_schema()

    budget = args.budget if args.budget is not None else DEFAULT_DAILY_BUDGET
    quota = DailyQuota(args.db, "eulerpool", limit_per_day=budget)
    status = quota.status()
    print(f"Kuota hari ini: {status.used}/{status.limit} terpakai (sisa {status.remaining})")

    if status.remaining < 1:
        print("Kuota habis — berhenti. Reset tengah malam UTC.")
        return 2

    adapter = EulerpoolAdapter(quota=quota)

    if args.probe:
        report = adapter.probe()
        print(f"probe: {report.status} | {report.detail} | {report.sample_size} item")
        return 0 if report.status is ApiStatus.OK else 1

    try:
        hasil = adapter.fetch_all(limit_per_target=args.limit)
    except QuotaExceeded as exc:
        print(f"GAGAL: {exc}")
        return 2

    total_new = 0
    for target, items in hasil.items():
        print(f"\n=== {target} === {len(items)} berita relevan")
        for item in items[: args.show]:
            ts = item.published_at.strftime("%Y-%m-%d %H:%M") if item.published_at else "?"
            print(f"    [{ts}] {item.source:<24} {item.title[:52]}")

        if args.dry_run or not items:
            continue
        fetched_at = utcnow()
        rows = [(item.to_raw_article(fetched_at), item.payload or None) for item in items]
        inserted = db.save_raw_articles(rows)
        total_new += inserted
        print(f"  tersimpan: {inserted} baru dari {len(rows)}")

    sisa = quota.status()
    if args.dry_run:
        print(f"\n(dry-run) tidak ada yang ditulis. Kuota terpakai: {sisa.used}/{sisa.limit}")
    else:
        print(f"\nTotal baru: {total_new} | kuota: {sisa.used}/{sisa.limit}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="news_cli",
        description="Identifikasi API berita & tarik berita real-time (XAU/RATE_UST/SPX).",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("identify", help="Tampilkan penyedia API & feed RSS yang teridentifikasi")
    sp.set_defaults(func=cmd_identify)

    sp = sub.add_parser("health", help="Laporan kesehatan (API + RSS)")
    sp.add_argument("--json", action="store_true", help="keluaran JSON")
    sp.set_defaults(func=cmd_health)

    sp = sub.add_parser(
        "eulerpool",
        help="Tarik berita pasar Eulerpool (1 request untuk semua target, kuota dijaga)",
    )
    sp.add_argument("--db", default="data/finews.db")
    sp.add_argument("--limit", type=int, default=30, help="maks artikel per target")
    sp.add_argument("--show", type=int, default=3, help="tampilkan N judul per target")
    sp.add_argument(
        "--budget",
        type=int,
        default=None,
        help="batas request/hari untuk vendor ini (1-100, default 20)",
    )
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--probe", action="store_true", help="hanya cek kunci (1 request)")
    sp.set_defaults(func=cmd_eulerpool)

    sp = sub.add_parser("fetch", help="Tarik berita dan simpan ke raw_articles")
    sp.add_argument("--target", choices=[*LOCKED_TARGETS, "all"], default="all")
    sp.add_argument("--limit", type=int, default=20, help="maks berita per target")
    sp.add_argument("--show", type=int, default=5, help="jumlah baris ditampilkan")
    sp.add_argument("--db", default="data/finews.db")
    sp.add_argument("--dry-run", action="store_true", help="jangan tulis ke DB")
    sp.add_argument("--api-only", action="store_true", help="hanya API, tanpa RSS")
    sp.add_argument("--rss-only", action="store_true", help="hanya RSS, tanpa API")
    sp.set_defaults(func=cmd_fetch)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
