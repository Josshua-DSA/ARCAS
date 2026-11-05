"""Tarik 1 headline/hari (XAU / RATE_UST / SPX) untuk 6 bulan terakhir via Finnhub.

Kenapa Finnhub `company-news`: satu-satunya endpoint yang punya filter tanggal
di paket gratis, dan proxy ETF (GLD/GDX/TLT/SPY) memberi cakupan harian penuh —
`market-news` hanya 50 item terakhir, `marketaux` 3 artikel/request (dan ~370
request untuk 184 hari > kuota 100/hari).

Kuota: Finnhub 60 req/menit tanpa cap harian. 184 hari / jendela 7 hari x 6
simbol = 162 request, dijeda 1,05 dtk -> ~3 menit.

Pemilihan: skor `score_relevance` (kata kunci target x2 + makro x1), tie-break
timestamp terbaru. Seed tetap -> keluaran reproducible.

Pemakaian:
    PYTHONPATH=. ./venv/bin/python scripts/daily_headline.py --hari 184
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import time
from pathlib import Path

from backend.src.collect.news_api.client import ApiError, NewsAPIClient, env
from backend.src.collect.news_api.keywords import (
    TARGET_KEYWORDS,
    matches_target,
    score_relevance,
)

BASE = "https://finnhub.io/api/v1/company-news"
# Proxy ETF/indeks per target. XAUUSD & ^TNX tidak tersedia di endpoint ini.
# Rampatan: 6 simbol cukup untuk cakupan harian penuh (uji: 184/184 hari),
# dan 6 simbol lebih cepat ~2x daripada 11 tanpa kehilangan satu hari pun.
PROXIES: dict[str, tuple[str, ...]] = {
    "XAU": ("GLD", "GDX"),
    "RATE_UST": ("TLT", "IEF"),
    "SPX": ("SPY", "^GSPC"),
}
REGISTRY = Path("data/source_registry.yaml")
DEFAULT_OUT = Path("outputs/daily_headline_6m.csv")


def _sumber(sym: str) -> str:
    return f"finnhub:{sym}"


def tarik(
    client: NewsAPIClient,
    key: str,
    simbols: list[str],
    mulai: dt.date,
    sampai: dt.date,
    jeda: float,
    jendela: int,
) -> list[dict]:
    """Tarik semua berita untuk daftar simbol pada rentang tanggal."""
    hasil: list[dict] = []
    cur = mulai
    while cur < sampai:
        nxt = min(cur + dt.timedelta(days=jendela), sampai)
        for sym in simbols:
            try:
                data, _ = client.get_json(
                    BASE,
                    {"symbol": sym, "from": cur.isoformat(), "to": nxt.isoformat(), "token": key},
                )
            except ApiError as exc:
                print(f"  ! {sym} {cur}: {exc.detail[:80]}", file=sys.stderr)
                time.sleep(jeda * 3)
                continue
            if not isinstance(data, list):
                print(f"  ! {sym} {cur}: respons {type(data).__name__}", file=sys.stderr)
                continue
            for row in data:
                ts = row.get("datetime")
                if not ts:
                    continue
                hasil.append({**row, "_sym": sym,
                              "_dt": dt.datetime.fromtimestamp(int(ts), tz=dt.timezone.utc)})
            time.sleep(jeda)
        cur = nxt
        print(f"  {cur}: {len(hasil)} artikel terkumpul", file=sys.stderr)
    return hasil


def reg_bulan(rows: list[dict], target: str) -> list[tuple[int, int, dt.datetime, dict]]:
    """Skor tiap berita untuk target, urut skor desc lalu waktu desc."""
    kw = TARGET_KEYWORDS.get(target, ())
    skor: list[tuple[int, int, dt.datetime, dict]] = []
    for r in rows:
        teks = f"{r.get('headline') or ''} {r.get('summary') or ''}"
        if not matches_target(teks, target):
            continue
        spesifik = sum(1 for k in kw if k in teks.lower())
        skor.append((score_relevance(teks, target), spesifik, r["_dt"], r))
    skor.sort(key=lambda t: (t[0], t[1], t[2]), reverse=True)
    return skor


def _simpan_cache(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    paket = [
        {"headline": r.get("headline"), "summary": r.get("summary"),
         "source": r.get("source"), "url": r.get("url"),
         "datetime": r["_dt"].isoformat(), "_sym": r["_sym"]}
        for r in rows
    ]
    path.write_text(json.dumps(paket, ensure_ascii=False), encoding="utf-8")


def _muat_cache(path: Path) -> list[dict]:
    paket = json.loads(path.read_text(encoding="utf-8"))
    return [
        {**p, "_dt": dt.datetime.fromisoformat(p["datetime"]), "_sym": p["_sym"]}
        for p in paket
    ]


def main() -> int:
    ap = argparse.ArgumentParser(description="1 headline/hari: emas, suku bunga, atau S&P 500")
    ap.add_argument("--hari", type=int, default=183, help="mundur berapa hari (default 183)")
    ap.add_argument("--sampai", default=None, help="tanggal akhir YYYY-MM-DD (default hari ini UTC)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="path CSV keluaran")
    ap.add_argument("--json", action="store_true", help="tulis juga .json di sebelah CSV")
    ap.add_argument("--db", default=None, help="opsional: simpan ke raw_articles")
    ap.add_argument("--target", default="all", choices=["all", "XAU", "RATE_UST", "SPX"])
    ap.add_argument("--jeda", type=float, default=1.05, help="jeda antar request (dtk, 60/menit)")
    ap.add_argument("--jendela", type=int, default=14, help="lebar jendela request (hari)")
    ap.add_argument("--min-skor", type=int, default=2, help="skor relevansi minimum")
    ap.add_argument("--cache", default="outputs/headline_cache.json",
                    help="cache artikel mentah; kosongkan (--cache '') untuk selalu tarik")
    args = ap.parse_args()

    key = env("FINNHUB_API_KEY")
    if not key:
        raise SystemExit("FINNHUB_API_KEY tidak ada di environment/.env")

    sampai = dt.date.fromisoformat(args.sampai) if args.sampai else dt.datetime.now(dt.timezone.utc).date()
    mulai = sampai - dt.timedelta(days=args.hari)

    simbols = [s for t in PROXIES.values() for s in t]
    cache = Path(args.cache) if args.cache else None
    if cache and cache.exists():
        rows = _muat_cache(cache)
        print(f"cache: {len(rows)} artikel dari {cache}", file=sys.stderr)
    else:
        print(f"tarik {mulai} .. {sampai} | {len(simbols)} simbol", file=sys.stderr)
        rows = tarik(NewsAPIClient(), key, simbols, mulai, sampai, args.jeda, args.jendela)
        print(f"total artikel mentah: {len(rows)}", file=sys.stderr)
        if cache:
            _simpan_cache(cache, rows)

    # Pilih 1 berita/hari: gabungkan skor semua target yang diizinkan.
    target_dipilih = list(PROXIES) if args.target == "all" else [args.target]
    per_hari: dict[str, dict] = {}
    for t in target_dipilih:
        for skor, spesifik, waktu, row in reg_bulan(rows, t):
            if skor < args.min_skor:
                continue
            hari = waktu.date().isoformat()
            lama = per_hari.get(hari)
            if lama is None or (skor, spesifik, waktu) > (lama["_skor"], lama["_spesifik"], lama["_waktu"]):
                per_hari[hari] = {
                    "tanggal": hari,
                    "target": t,
                    "judul": (row.get("headline") or "").strip(),
                    "sumber": row.get("source") or "",
                    "url": row.get("url") or "",
                    "waktu_utc": waktu.isoformat(),
                    "skor": skor,
                    "simbol": row["_sym"],
                    "ringkasan": (row.get("summary") or "").strip()[:300],
                    "_skor": skor,
                    "_spesifik": spesifik,
                    "_waktu": waktu,
                }

    kolom = ["tanggal", "target", "judul", "sumber", "url", "waktu_utc", "skor", "simbol", "ringkasan"]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    urut = [per_hari[k] for k in sorted(per_hari)]
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=kolom, extrasaction="ignore")
        w.writeheader()
        w.writerows(urut)

    if args.json:
        out.with_suffix(".json").write_text(
            json.dumps(urut, ensure_ascii=False, indent=1, default=str), encoding="utf-8"
        )

    if args.db:
        from backend.src.schema import RawArticle
        from backend.src.store.db import Database

        now = dt.datetime.now(dt.timezone.utc)
        batch: list[tuple[RawArticle, dict | None]] = [
            (RawArticle(
                source=f"finnhub:headline:{r['simbol']}",
                url=r["url"] or None,
                title=r["judul"][:500],
                body=r["ringkasan"] or None,
                published_at=r["_waktu"],
                fetched_at=now,
                query_target=r["target"],
            ), None)
            for r in urut
        ]
        print(f"DB: {Database(args.db).save_raw_articles(batch)} baris baru", file=sys.stderr)

    allday = {mulai + dt.timedelta(days=i) for i in range((sampai - mulai).days + 1)}
    kosong = sorted(d.isoformat() for d in allday - {dt.date.fromisoformat(k) for k in per_hari})
    per_target: dict[str, int] = {}
    for r in urut:
        per_target[r["target"]] = per_target.get(r["target"], 0) + 1

    print("\n=== HASIL ===")
    print(f"  hari diminta : {len(allday)}")
    print(f"  hari terisi  : {len(urut)}")
    print(f"  hari kosong  : {len(kosong)}" + (f" -> {kosong[:10]}" if kosong else ""))
    print(f"  per target   : {per_target}")
    print(f"  CSV          : {out.resolve()}")
    return 0 if urut else 1


if __name__ == "__main__":
    raise SystemExit(main())
