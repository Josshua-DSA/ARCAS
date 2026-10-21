"""Uji `news_cli` (backend/src/collect/news_cli.py).

Modul ini sebelumnya **nol test**. Yang diuji sengaja hanya bagian yang
deterministik dan tidak butuh jaringan: dedupe lintas penyedia, pencatatan
kesehatan ke `source_health`, logika alert, dan pembentukan parser/argumen.

Jalur yang memanggil API sungguhan (`identify`, `health`, `fetch`) tidak
dipanggil ke jaringan di sini -- itu akan membuat CI rapuh. Yang penting dari
jalur tersebut adalah kontraknya: `_record_health` harus menulis status dan
mengembalikan alert, dan `_dedupe` harus membuang duplikat judul.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import pytest

from backend.src.collect.news_api.base import NewsItem
from backend.src.collect.news_cli import (
    _dedupe,
    _print_alerts,
    _record_health,
    build_parser,
    main,
)
from backend.src.store.db import Database


@pytest.fixture
def db(tmp_path):
    d = Database(str(tmp_path / "news.db"))
    d.init_schema()
    return d


def _item(title: str, source: str = "wire", target: str = "XAU") -> NewsItem:
    return NewsItem(
        source=source,
        title=title,
        url=f"https://contoh.test/{abs(hash(title))}",
        body="isi",
        published_at=datetime(2026, 1, 5, tzinfo=timezone.utc),
        query_target=target,
    )


# ---------------------------------------------------------------------------
# Dedupe
# ---------------------------------------------------------------------------


def test_dedupe_removes_identical_titles():
    items = [_item("Emas naik"), _item("Emas naik")]
    assert len(_dedupe(items)) == 1


def test_dedupe_ignores_case_and_whitespace():
    """Judul beda kapitalisasi/spasi dianggap sama -- ini yang terjadi nyata
    saat penyedia yang sama menulis ulang judul."""
    items = [_item("Emas   Naik  Tajam"), _item("emas naik tajam")]
    assert len(_dedupe(items)) == 1


def test_dedupe_case_folding_is_what_makes_them_match():
    """Kunci yang tepat: perbandingan harus case-insensitive.

    Kalau `lower()` dihapus, `_dedupe` hanya menyamakan judul yang identik
    persis (karena normalisasi spasi tetap jalan), sehingga pasangan ini
    lolos sebagai dua berita. Test ini yang menangkap regresi tersebut.
    """
    assert len(_dedupe([_item("Emas Naik Tajam"), _item("emas naik tajam")])) == 1
    # Kontrol: tanpa case-folding keduanya berbeda, jadi tetap harus beda
    # saat kapitalisasinya memang berbeda secara sengaja.
    assert len(_dedupe([_item("EMAS"), _item("emas")])) == 1


def test_dedupe_keeps_distinct_titles():
    items = [_item("Emas naik"), _item("Dolar melemah")]
    assert len(_dedupe(items)) == 2


def test_dedupe_preserves_first_occurrence_order():
    items = [_item("A"), _item("B"), _item("A")]
    out = _dedupe(items)
    assert [i.title for i in out] == ["A", "B"]


def test_dedupe_empty_list():
    assert _dedupe([]) == []


def test_dedupe_truncates_long_titles_before_comparing():
    """Dua judul yang hanya beda di ekor (setelah 120 char) dianggap sama."""
    base = "x" * 130
    assert len(_dedupe([_item(base + "AAA"), _item(base + "BBB")])) == 1


# ---------------------------------------------------------------------------
# Pencatatan kesehatan & alert
# ---------------------------------------------------------------------------


def test_record_health_writes_api_and_rss_rows(db):
    _record_health(
        db,
        apis=[
            {
                "provider": "finnhub",
                "status": "ok",
                "detail": "",
                "latency_ms": 12.5,
                "sample_size": 3,
                "usable": True,
            }
        ],
        rss=[{"feed": "antara", "status": "ok", "items": 5, "detail": ""}],
    )

    with db.get_connection() as conn:
        rows = conn.execute("SELECT source FROM source_health ORDER BY source").fetchall()
    assert [r["source"] for r in rows] == ["api:finnhub", "rss:antara"]


def test_no_alert_below_threshold(db):
    alerts: list[dict] = []
    for _ in range(2):
        alerts = _record_health(
            db,
            apis=[{"provider": "x", "status": "error", "detail": "boom", "usable": False}],
            rss=[],
        )
    assert alerts == []


def test_alert_fires_on_third_consecutive_failure(db):
    alerts: list[dict] = []
    for _ in range(3):
        alerts = _record_health(
            db,
            apis=[{"provider": "x", "status": "error", "detail": "boom", "usable": False}],
            rss=[],
        )

    assert len(alerts) == 1
    assert alerts[0]["source"] == "api:x"
    assert alerts[0]["consecutive_failures"] == 3


def test_alert_stops_after_source_recovers(db):
    """Kegagalan lama tidak boleh membuat alert terus berbunyi setelah pulih."""
    for _ in range(3):
        _record_health(
            db,
            apis=[{"provider": "x", "status": "error", "detail": "boom", "usable": False}],
            rss=[],
        )
    # Sumber pulih
    alerts = _record_health(
        db,
        apis=[{"provider": "x", "status": "ok", "detail": "", "usable": True}],
        rss=[],
    )
    assert alerts == []


def test_record_health_returns_list_not_none(db):
    out = _record_health(db, apis=[], rss=[])
    assert isinstance(out, list)
    assert out == []


def test_print_alerts_silent_when_empty(capsys):
    _print_alerts([])
    assert capsys.readouterr().out == ""


def test_print_alerts_shows_source_and_streak(capsys):
    _print_alerts(
        [
            {
                "source": "api:finnhub",
                "consecutive_failures": 4,
                "status": "error",
                "detail": "timeout",
            }
        ]
    )
    out = capsys.readouterr().out
    assert "ALERT" in out
    assert "api:finnhub" in out
    assert "4x" in out


# ---------------------------------------------------------------------------
# Parser & wiring
# ---------------------------------------------------------------------------


def test_parser_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_parser_fetch_defaults():
    args = build_parser().parse_args(["fetch"])
    assert args.target == "all"
    assert args.limit == 20
    assert args.dry_run is False


def test_parser_rejects_unknown_target():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["fetch", "--target", "BTC"])


def test_parser_accepts_locked_targets():
    for target in ("XAU", "RATE_UST", "SPX"):
        args = build_parser().parse_args(["fetch", "--target", target])
        assert args.target == target


def test_parser_sets_dispatch_function():
    args = build_parser().parse_args(["identify"])
    assert callable(args.func)


def test_parser_health_json_flag():
    args = build_parser().parse_args(["health", "--json"])
    assert args.json is True


def test_main_returns_handler_exit_code(monkeypatch):
    """`main` harus memanggil handler untuk subperintah dan meneruskan hasilnya."""
    import backend.src.collect.news_cli as mod

    def fake_identify(args: argparse.Namespace) -> int:
        return 7

    # `main` membangun parser sendiri, jadi ganti fungsi sebelum main dipanggil
    # tidak cukup -- parser menyimpan referensi saat dibangun. Karena itu kita
    # uji lewat handler yang benar-benar dipakai parser: cmd_identify.
    original = mod.cmd_identify

    def patched(args: argparse.Namespace) -> int:
        return 7

    mod.cmd_identify = patched
    try:
        # Parser dibangun di dalam main() -> akan menangkap fungsi yang dipatch.
        assert main(["identify"]) == 7
    finally:
        mod.cmd_identify = original
