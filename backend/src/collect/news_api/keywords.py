"""Kata kunci relevansi target — dibaca dari `data/source_registry.yaml`.

Registry adalah SATU-SATUNYA sumber kebenaran. Sebelumnya daftar di sini
disalin manual dari YAML, dan keduanya sudah menyimpang (kode 15/22/17 kata,
YAML 9/8/8) sementara docstring mengaku bersumber dari YAML. Dokumen yang
berbohong lebih buruk daripada tidak ada dokumen: orang mengedit YAML lalu
bingung kenapa tidak ada efeknya.

Sekarang YAML dibaca saat impor. Menambah kata kunci cukup di YAML.

Pencocokan memakai word-boundary regex, bukan substring. Tanpa ini kata kunci
pendek seperti "war" akan cocok di "software", "award", "toward", "hardware"
dan meloloskan berita yang sama sekali tidak relevan.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

DEFAULT_REGISTRY_PATH = Path("data/source_registry.yaml")

# Cadangan bila registry tidak terbaca (mis. dijalankan dari cwd lain).
# Sengaja MINIMAL, bukan salinan penuh: daftar panjang di sini akan kembali
# menjadi sumber kebenaran kedua yang lambat laun menyimpang lagi. Tujuannya
# hanya menjaga program tetap hidup, dan `registry_source` menandainya.
_FALLBACK_TARGETS: dict[str, tuple[str, ...]] = {
    "XAU": ("gold", "bullion", "xau"),
    "RATE_UST": ("treasury", "yield", "fomc"),
    "SPX": ("s&p 500", "spx", "stocks"),
}
_FALLBACK_MACRO: tuple[str, ...] = ("fed", "inflation", "war")


def _load_registry(
    path: Path | None = None,
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...], str]:
    """Baca `targets.<ID>.keywords` dan `macro.keywords` dari registry.

    Returns:
        (kata kunci per target, kata kunci makro, keterangan sumber)
    """
    reg_path = path or DEFAULT_REGISTRY_PATH
    if not reg_path.exists():
        return dict(_FALLBACK_TARGETS), _FALLBACK_MACRO, f"fallback:{reg_path} tidak ada"

    try:
        data = yaml.safe_load(reg_path.read_text(encoding="utf-8")) or {}
    except (yaml.YAMLError, OSError) as exc:
        return dict(_FALLBACK_TARGETS), _FALLBACK_MACRO, f"fallback:gagal baca ({exc})"

    raw_targets = data.get("targets") or {}
    targets: dict[str, tuple[str, ...]] = {}
    for target_id, spec in raw_targets.items():
        if not isinstance(spec, dict):
            continue
        words = spec.get("keywords") or []
        # Dedup sambil pertahankan urutan; YAML boleh berisi duplikat.
        seen: dict[str, None] = {}
        for w in words:
            text = str(w).strip().lower()
            if text:
                seen.setdefault(text, None)
        if seen:
            targets[str(target_id)] = tuple(seen)

    macro_raw = ((data.get("macro") or {}).get("keywords")) or []
    macro_seen: dict[str, None] = {}
    for w in macro_raw:
        text = str(w).strip().lower()
        if text:
            macro_seen.setdefault(text, None)

    if not targets:
        return dict(_FALLBACK_TARGETS), _FALLBACK_MACRO, "fallback:targets kosong"

    version = data.get("version", "tanpa-versi")
    return targets, tuple(macro_seen), f"registry:{version}"


TARGET_KEYWORDS, MACRO_KEYWORDS, REGISTRY_SOURCE = _load_registry()

# Kata kunci makro: menambah skor, tetapi TIDAK cukup sendirian untuk
# meloloskan berita — butuh minimal satu kata kunci target-spesifik.


@lru_cache(maxsize=256)
def _pattern(keyword: str) -> re.Pattern[str]:
    """Kompilasi kata kunci menjadi regex word-boundary, case-insensitive.

    Spasi di dalam frasa dilonggarkan agar "safe haven" juga cocok dengan
    "safe-haven" dan "safe  haven".
    """
    parts = [re.escape(p) for p in re.split(r"[\s\-]+", keyword.strip()) if p]
    body = r"[\s\-]*".join(parts)
    return re.compile(rf"(?<!\w){body}(?!\w)", re.IGNORECASE)


def count_hits(text: str, keywords: tuple[str, ...]) -> int:
    """Jumlah kata kunci berbeda yang cocok di teks."""
    return sum(1 for kw in keywords if _pattern(kw).search(text))


def score_relevance(text: str, target: str) -> int:
    """Skor relevansi: 2x kata kunci target + 1x kata kunci makro.

    Skor 0 berarti tidak relevan sama sekali.
    """
    if not text:
        return 0
    specific = count_hits(text, TARGET_KEYWORDS.get(target, ()))
    macro = count_hits(text, MACRO_KEYWORDS)
    return specific * 2 + macro


def matches_target(text: str, target: str, require_specific: bool = True) -> bool:
    """True bila teks relevan untuk target.

    `require_specific=True` (default) menolak berita yang hanya cocok dengan
    kata kunci makro seperti "inflation" tanpa menyebut targetnya.
    """
    if not text:
        return False
    specific = count_hits(text, TARGET_KEYWORDS.get(target, ()))
    if require_specific and specific == 0:
        return False
    return (specific > 0) or (count_hits(text, MACRO_KEYWORDS) > 0)
