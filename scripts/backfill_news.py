"""Backfill berita historis 1 tahun dari Marketaux ke raw_articles.

Kenapa modul terpisah: `news_cli fetch` hanya menarik berita terbaru karena
semua adapter tidak punya parameter tanggal. Marketaux sebenarnya mendukung
`published_after` / `published_before`, jadi backfill butuh jalur sendiri.

Batas nyata yang ditemukan saat uji (dicatat supaya tidak jadi tebakan):
- Paket gratis Marketaux mengembalikan **3 artikel per request**, berapapun
  `limit` yang diminta. `meta.found` bisa 29.925 tapi `returned` selalu 3.
- Paginasi (`page`) tidak dibatasi, jadi 3 artikel x N halaman.
- Cloudflare menolak urllib polos (error 1010); harus lewat NewsAPIClient
  yang mengirim User-Agent wajar.
- Yield kata kunci rendah: XAU ~0-8%, RATE_UST ~3%, SPX ~36% dari berita
  pasar AS. Berita emas/obligasi AS jarang menyebut instrumennya langsung.

Prinsip:
- Idempoten: `save_raw_articles` melewati duplikat (source,url)/(source,title),
  jadi menjalankan ulang tidak menggandakan apa pun.
- Resumable: progres per (bulan) ditulis ke berkas state; berhenti kapan saja,
  lanjut lagi tanpa mengulang bulan yang sudah selesai.
- Sopan: jeda tetap antar request, retry dengan backoff, dan --max-requests
  sebagai pagar supaya satu kali jalan tidak menghabiskan kuota.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from backend.src.collect.news_api.keywords import matches_target
from backend.src.collect.news_api.marketaux import MarketauxAdapter
from backend.src.schema import RawArticle
from backend.src.store.db import Database

STATE_DEFAULT = Path("data/backfill_state.json")
BASE = "https://api.marketaux.com/v1/news/all"
ARTIKEL_PER_REQUEST = 3          # plafon nyata paket gratis; bukan pilihan kita
TARGETS = ("XAU", "RATE_UST", "SPX")


def _bulan(dari: datetime, sampai: datetime) -> list[tuple[datetime, datetime]]:
    """Potong rentang jadi jendela ~30 hari, dibatasi `sampai`."""
    out = []
    cur = dari
    while cur < sampai:
        nxt = min(cur + timedelta(days=30), sampai)
        out.append((cur, nxt))
        cur = nxt
    return out


def _muat_state(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"  ! state rusak, mulai dari nol: {path}", file=sys.stderr)
    return {"selesai": []}


def _simpan_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    tmp.replace(path)  # tulis atomik: state tidak setengah jadi


def _teks(row: dict) -> str:
    return " ".join(
        str(row.get(k) or "") for k in ("title", "description", "snippet")
    )


def backfill(
    db_path: str,
    hari: int,
    state_path: Path,
    max_requests: int,
    jeda: float,
    halaman_per_jendela: int,
) -> dict:
    now = datetime.now(timezone.utc)
    mulai = now - timedelta(days=hari)
    adapter = MarketauxAdapter()
    if not adapter.is_configured():
        raise SystemExit("MARKETAUX_API_KEY tidak ada di environment/.env")

    db = Database(db_path)
    state = _muat_state(state_path)
    selesai = set(state.get("selesai", []))

    stat = {"request": 0, "artikel": 0, "baru": 0, "relevan": 0, "jendela": 0, "berhenti": None}
    # sisa kuota per target, hanya untuk laporan
    dapet = {t: 0 for t in TARGETS}

    for a0, a1 in _bulan(mulai, now):
        kunci = a0.strftime("%Y-%m-%d")
        if kunci in selesai:
            continue
        if stat["request"] >= max_requests:
            stat["berhenti"] = "max_requests"
            break
        stat["jendela"] += 1
        jendela_baru = 0

        for page in range(1, halaman_per_jendela + 1):
            if stat["request"] >= max_requests:
                stat["berhenti"] = "max_requests"
                break
            params = {
                "countries": "us",
                "filter_entities": "true",
                "language": "en",
                "limit": ARTIKEL_PER_REQUEST,
                "page": page,
                "api_token": adapter._key,  # noqa: SLF001 - adapter tak punya API publik
                "published_after": a0.strftime("%Y-%m-%dT%H:%M:%S"),
                "published_before": a1.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            try:
                data, _ = adapter.client.get_json(BASE, params)
            except Exception as exc:  # noqa: BLE001 - satu halaman gagal tidak fatal
                print(f"  ! {kunci} hal.{page} gagal: {type(exc).__name__}: {str(exc)[:120]}",
                      file=sys.stderr)
                time.sleep(jeda * 2)
                continue
            stat["request"] += 1

            rows = data.get("data") or []
            if not rows:
                break

            batch: list[tuple[RawArticle, dict | None]] = []
            for row in rows:
                teks = _teks(row)
                cocok = [t for t in TARGETS if matches_target(teks, t)]
                if not cocok:
                    continue
                stat["relevan"] += 1
                for t in cocok:
                    dapet[t] += 1
                pub = row.get("published_at")
                try:
                    pub_dt = (
                        datetime.fromisoformat(str(pub).replace("Z", "+00:00"))
                        if pub else None
                    )
                except ValueError:
                    pub_dt = None
                batch.append((
                    RawArticle(
                        source=f"marketaux:backfill:{cocok[0]}",
                        url=row.get("url"),
                        title=str(row.get("title") or "")[:500],
                        body=teks[:4000] or None,
                        published_at=pub_dt,
                        fetched_at=now,
                        query_target=cocok[0],
                        vendor_sentiment=None,
                    ),
                    row,
                ))
            if batch:
                stat["baru"] += db.save_raw_articles(batch)
                jendela_baru += len(batch)
            stat["artikel"] += len(rows)

            if len(rows) < ARTIKEL_PER_REQUEST:
                break  # halaman terakhir jendela ini
            time.sleep(jeda)

        # Jendela dianggap selesai hanya bila tidak terpotong pagar request.
        if stat["berhenti"] is None:
            selesai.add(kunci)
            state["selesai"] = sorted(selesai)
            _simpan_state(state_path, state)
        print(f"  {kunci}: {jendela_baru:3} artikel relevan | total request {stat['request']}")

    return {**stat, "per_target": dapet}


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill berita historis dari Marketaux")
    ap.add_argument("--db", default="data/finews.db")
    ap.add_argument("--hari", type=int, default=365, help="mundur berapa hari (default 365)")
    ap.add_argument("--state", default=str(STATE_DEFAULT))
    ap.add_argument("--max-requests", type=int, default=200,
                    help="pagar request untuk satu kali jalan (default 200)")
    ap.add_argument("--jeda", type=float, default=0.6, help="jeda antar request (detik)")
    ap.add_argument("--halaman-per-jendela", type=int, default=20,
                    help="maks halaman per jendela 30 hari (default 20 = 60 artikel)")
    ap.add_argument("--dry-run", action="store_true", help="hitung tanpa menulis DB")
    args = ap.parse_args()

    if args.dry_run:
        now = datetime.now(timezone.utc)
        j = _bulan(now - timedelta(days=args.hari), now)
        print(f"dry-run: {len(j)} jendela x {args.halaman_per_jendela} halaman")
        print(f"  maks request: {min(len(j)*args.halaman_per_jendela, args.max_requests)}")
        print(f"  maks artikel: {min(len(j)*args.halaman_per_jendela, args.max_requests)*ARTIKEL_PER_REQUEST}")
        return 0

    print(f"backfill {args.hari} hari -> {args.db}")
    print(f"  {ARTIKEL_PER_REQUEST} artikel/request, pagar {args.max_requests} request")
    stat = backfill(args.db, args.hari, Path(args.state), args.max_requests,
                    args.jeda, args.halaman_per_jendela)
    print("\n=== HASIL ===")
    print(f"  request     : {stat['request']}")
    print(f"  artikel     : {stat['artikel']}")
    print(f"  relevan     : {stat['relevan']}")
    print(f"  baru di DB  : {stat['baru']}")
    print(f"  per target  : {stat['per_target']}")
    if stat["berhenti"]:
        print(f"  berhenti    : {stat['berhenti']} (jalankan ulang untuk lanjut)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
