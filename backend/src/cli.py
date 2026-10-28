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


def cmd_ingest(args: argparse.Namespace) -> int:
    """Impor artikel manual dari CSV/JSON ke raw_articles (FR-1).

    Baris buruk dilewati dengan alasan dan dilaporkan; proses tidak berhenti.
    Deduplikasi ditangani Database.save_raw_articles yang idempoten lewat
    (source, url) atau (source, title), jadi menjalankan ulang file yang sama
    tidak menggandakan baris.
    """
    from backend.src.collect.manual_ingest import baca_file, bangun_artikel

    path = Path(args.file)
    try:
        baris = baca_file(path, args.format)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Gagal membaca {path}: {exc}")
        return 1

    hasil = bangun_artikel(baris)

    print(f"Dibaca   : {hasil.dibaca} baris dari {path}")
    print(f"Valid    : {hasil.jumlah_siap}")
    print(f"Dilewati : {len(hasil.dilewati)}")
    for skip in hasil.dilewati:
        print(f"  baris {skip.baris}: {skip.alasan}")

    if not hasil.siap:
        print("Tidak ada baris valid — tidak ada yang ditulis.")
        return 1

    if args.dry_run:
        print("\n=== DRY RUN — tidak ada yang ditulis ===")
        for artikel in hasil.siap[:3]:
            print(f"  [{artikel.source}] {artikel.title[:60]}")
        if hasil.jumlah_siap > 3:
            print(f"  ... dan {hasil.jumlah_siap - 3} lainnya")
        return 0

    db = Database(Path(args.db))
    # init_schema idempoten (DDL memakai IF NOT EXISTS), jadi aman dipanggil
    # baik untuk DB baru maupun yang sudah berisi.
    db.init_schema()
    ditulis = db.save_raw_articles([(artikel, None) for artikel in hasil.siap])
    print(f"Ditulis  : {ditulis} artikel baru ke raw_articles")
    if ditulis < hasil.jumlah_siap:
        print(
            f"  ({hasil.jumlah_siap - ditulis} dilewati karena sudah ada "
            "— dedup berdasarkan source+url/title)"
        )
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


# ---------------------------------------------------------------------------
# T-2: perintah bertahap (FR-14)
# ---------------------------------------------------------------------------


def cmd_clean(args: argparse.Namespace) -> int:
    """raw_articles -> articles saja."""
    if args.dry_run:
        print("=== DRY RUN — tidak ada yang ditulis ===\n")
    try:
        pipe = Pipeline(db_path=args.db)
        articles, stats = pipe.normalize_raw(limit=args.limit, dry_run=args.dry_run)
    except PipelineError as exc:
        print(f"GAGAL: {exc}")
        return 1

    print(f"raw dibaca     : {stats.raw_dibaca}")
    print(f"articles siap  : {len(articles)}")
    print(f"ditulis        : {stats.artikel_tertulis}")
    if stats.errors:
        print(f"\nerror          : {len(stats.errors)}")
        for err in stats.errors[:5]:
            print(f"  - {err}")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    """articles -> sentiments + impacts."""
    if args.dry_run:
        print("=== DRY RUN — tidak ada yang ditulis ===\n")
    try:
        pipe = Pipeline(db_path=args.db, model_path=args.model)
        # S-4: dulu `normalize_raw(dry_run=True)`, sehingga tahap ini mengolah
        # ulang raw_articles dan bukan memakai hasil `clean`. Sekarang benar-
        # benar membaca tabel `articles`.
        articles = pipe.load_articles(limit=args.limit)
        if not articles:
            print(
                "Tidak ada artikel di tabel `articles`. Jalankan `clean` lebih dulu:\n"
                f"  python -m backend.src.cli --db {args.db} clean"
            )
            return 1
        impacts, stats = pipe.score_and_route(articles, dry_run=args.dry_run)
    except PipelineError as exc:
        print(f"GAGAL: {exc}")
        return 1

    print(f"artikel diskor : {len(articles)}")
    print(f"impact dibuat  : {len(impacts)}")
    print(f"sentimen tulis : {stats.sentimen_tertulis}")
    print(f"impact tulis   : {stats.impact_tertulis}")
    if stats.errors:
        print(f"\nerror          : {len(stats.errors)}")
        for err in stats.errors[:5]:
            print(f"  - {err}")
    return 0


def cmd_aggregate(args: argparse.Namespace) -> int:
    """impacts -> daily_sentiment."""
    if args.dry_run:
        print("=== DRY RUN — tidak ada yang ditulis ===\n")
    try:
        pipe = Pipeline(db_path=args.db, model_path=args.model)
        articles, _ = pipe.normalize_raw(limit=args.limit, dry_run=True)
        if not articles:
            print("Tidak ada artikel. Jalankan `clean` lalu `score` dulu.")
            return 0
        impacts, _ = pipe.score_and_route(articles, dry_run=True)
        stats = pipe.aggregate(impacts, articles, dry_run=args.dry_run)
    except PipelineError as exc:
        print(f"GAGAL: {exc}")
        return 1

    print(f"baris harian   : {stats.hari_agregat}")
    if stats.errors:
        print(f"\nerror          : {len(stats.errors)}")
        for err in stats.errors[:5]:
            print(f"  - {err}")
    return 0


def cmd_check_schema(args: argparse.Namespace) -> int:
    """Laporkan selisih skema DB terhadap yang diharapkan kode (P3-5).

    Hanya membaca; tidak pernah mengubah apa pun. Dipakai untuk mendeteksi DB
    yang tertinggal SEBELUM query-nya gagal di produksi. Kode keluar 1 bila ada
    yang tidak beres, supaya bisa dipakai di CI.
    """
    db = Database(args.db)
    if not db.db_path.exists():
        print(f"DB tidak ditemukan: {db.db_path}")
        return 1

    with db.get_connection() as conn:
        versi = db.versi_skema(conn)
        hilang = db.skema_tidak_lengkap(conn)

    print(f"db       : {db.db_path}")
    print(f"versi    : {versi} (diharapkan {Database.SCHEMA_VERSION})")
    if hilang:
        print(f"hilang   : {len(hilang)} kolom/tabel")
        for item in hilang:
            print(f"  - {item}")
        print("\nJalankan `fi pipeline` atau buka aplikasi sekali untuk memigrasi.")
        return 1

    print("skema    : lengkap")
    if versi < Database.SCHEMA_VERSION:
        print(f"peringatan: versi DB lebih lama dari kode ({versi} < {Database.SCHEMA_VERSION})")
        return 1
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    """Hitung OLS HAC + Granger per aset, simpan ke stat_results."""
    import pandas as pd

    from backend.src.stats.engine import StatEngine

    db = Database(args.db)
    db.init_schema()
    universe = db.get_active_universe() or []
    asset_ids = [a.get("asset_id") for a in universe if a.get("asset_id")]
    if not asset_ids:
        print("Universe kosong. Jalankan `seed` dulu.")
        return 1

    total = 0
    for raw_asset_id in asset_ids:
        asset_id: str = str(raw_asset_id)
        rows = db.get_daily_series(asset_id)
        if not rows:
            print(f"  {asset_id:<9} tidak ada harga — dilewati")
            continue

        df = pd.DataFrame(rows)
        df["date"] = pd.to_datetime(df["date"])
        n_paired = int(df["score_mean"].notna().sum()) if "score_mean" in df else 0

        ols = StatEngine.compute_ols_hac(df, asset_id, max_lag=args.max_lag)
        granger = StatEngine.compute_granger(df, asset_id, max_lag=args.max_lag)
        hasil = ols + granger

        if not args.dry_run:
            for res in hasil:
                db.save_stat(res)

        total += len(hasil)
        if hasil:
            print(f"  {asset_id:<9} {n_paired} hari berpasangan -> {len(ols)} OLS, {len(granger)} Granger")
            for res in hasil[: args.show]:
                adj = f"{res.p_adjusted:.4f}" if res.p_adjusted is not None else "—"
                print(
                    f"      {res.test:<8} lag={res.lag} est={res.estimate:+.5f} "
                    f"p={res.p_value:.4f} p_adj={adj} n={res.n_obs}"
                )
        else:
            print(
                f"  {asset_id:<9} {n_paired} hari berpasangan -> 0 hasil "
                f"(butuh >= 10 hari berpasangan)"
            )

    print(f"\nTotal {total} baris statistik {'(dry-run, tidak disimpan)' if args.dry_run else 'tersimpan'}.")
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Ekspor dataset olahan ke Parquet (FR-13: SQLite + Parquet).

    S-3: `ParquetStore` sudah berfungsi sejak awal tetapi tidak dipanggil
    siapa pun — kode mati. Perintah ini menjadikannya jalur nyata: SQLite tetap
    sumber kebenaran operasional, Parquet untuk dump massal dan dataset latih.
    """
    import pandas as pd

    from backend.src.store.parquet_store import ParquetStore

    db = Database(args.db)
    db.init_schema()
    store = ParquetStore(base_dir=args.out)

    dengan_conn = db.get_connection()
    with dengan_conn as conn:
        frames: dict[str, pd.DataFrame] = {}
        for nama, query in (
            (
                "daily_sentiment",
                "SELECT * FROM daily_sentiment ORDER BY asset_id, date;",
            ),
            ("prices", "SELECT * FROM prices ORDER BY asset_id, date;"),
            (
                "impacts",
                "SELECT article_id, asset_id, direction, score, confidence, basis,"
                " news_horizon, model_version, created_at FROM impacts"
                " ORDER BY article_id, asset_id;",
            ),
        ):
            try:
                frames[nama] = pd.read_sql_query(query, conn)
            except Exception as exc:  # noqa: BLE001 - tabel bisa belum ada
                print(f"  lewati {nama}: {exc}")
                continue

    if not frames:
        print("Tidak ada tabel yang bisa diekspor.")
        return 1

    for nama, df in frames.items():
        if df.empty:
            print(f"  {nama:<16} kosong, dilewati")
            continue
        path = store.write_dataset(nama, df)
        print(f"  {nama:<16} {len(df):>6} baris -> {path}")

    print(f"\nSelesai. Direktori: {args.out}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Ekspor outputs/report.html mandiri (RULES.md:144)."""
    from backend.src.report.exporter import ReportExporter

    db = Database(args.db)
    db.init_schema()
    universe = db.get_active_universe() or []

    with db.get_connection() as conn:
        try:
            rows = conn.execute(
                "SELECT * FROM stat_results ORDER BY asset_id, test, lag;"
            ).fetchall()
        except Exception:  # noqa: BLE001 - tabel belum ada pada DB lama
            rows = []
    stats_rows = [dict(r) for r in rows]

    exporter = ReportExporter(output_dir=args.out)
    out = exporter.export_html_report(
        universe=universe,
        stats=stats_rows,
        allocations={},
        report_name=args.name,
    )
    ukuran = Path(out).stat().st_size
    print(f"Laporan ditulis: {out} ({ukuran:,} byte)")
    print(f"  universe : {len(universe)} aset")
    print(f"  statistik: {len(stats_rows)} baris")
    if not stats_rows:
        print("  catatan  : belum ada hasil statistik — jalankan `stats` dulu.")
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

    sp = sub.add_parser("ingest", help="impor artikel manual dari CSV/JSON")
    sp.add_argument("--file", required=True, help="path file .csv atau .json")
    sp.add_argument(
        "--format",
        choices=("csv", "json"),
        default=None,
        help="format file; kalau kosong ditebak dari ekstensi",
    )
    sp.add_argument(
        "--dry-run", action="store_true", help="validasi saja, jangan tulis ke DB"
    )
    sp.set_defaults(func=cmd_ingest)

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

    sp = sub.add_parser("clean", help="raw_articles -> articles")
    sp.add_argument("--limit", type=int, default=1000, help="maks raw diproses")
    sp.add_argument("--dry-run", action="store_true", help="hitung saja, jangan tulis")
    sp.set_defaults(func=cmd_clean)

    sp = sub.add_parser("score", help="articles -> sentiments + impacts")
    sp.add_argument("--limit", type=int, default=1000)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--model", default="model/common/baseline_tfidf.joblib")
    sp.set_defaults(func=cmd_score)

    sp = sub.add_parser("aggregate", help="impacts -> daily_sentiment")
    sp.add_argument("--limit", type=int, default=1000)
    sp.add_argument("--dry-run", action="store_true")
    sp.add_argument("--model", default="model/common/baseline_tfidf.joblib")
    sp.set_defaults(func=cmd_aggregate)

    sp = sub.add_parser("stats", help="hitung OLS HAC + Granger")
    sp.add_argument("--max-lag", type=int, default=5, help="lag maksimum")
    sp.add_argument("--show", type=int, default=3, help="tampilkan N hasil per aset")
    sp.add_argument("--dry-run", action="store_true")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("export", help="ekspor dataset olahan ke Parquet")
    sp.add_argument("--out", default="data/processed", help="direktori keluaran")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("report", help="ekspor outputs/report.html")
    sp.add_argument("--out", default="outputs", help="direktori keluaran")
    sp.add_argument("--name", default="report.html")
    sp.set_defaults(func=cmd_report)

    sp = sub.add_parser(
        "check-schema", help="periksa apakah skema DB tertinggal dari kode (P3-5)"
    )
    sp.set_defaults(func=cmd_check_schema)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
