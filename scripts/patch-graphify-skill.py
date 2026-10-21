#!/usr/bin/env python3
"""Patch skill graphify agar menulis ke `.graphify/`, bukan `graphify-out/`.

Skill graphify adalah file *generated*: `graphify install --platform hermes`
menimpanya. Setiap upgrade graphify mengembalikan semua rujukan ke
`graphify-out/` dan menghapus instruksi `GRAPHIFY_OUT`. Script ini
memulihkannya, dan aman dijalankan berulang (idempoten).

Pakai:
    ./scripts/patch-graphify-skill.py           # patch semua salinan
    ./scripts/patch-graphify-skill.py --check   # hanya periksa, exit 1 bila basi

Kenapa perlu `GRAPHIFY_OUT`: nama direktori keluaran dibaca **sekali saat
import** di `graphify/paths.py`, dan tidak ada flag CLI untuk menggantinya.
Mengganti path di teks saja tidak cukup — perintah CLI tetap menulis ke
`graphify-out/` tanpa env var itu.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

MARKER = "MANDATORY — output directory override"

MANDATORY_BLOCK = f"""**{MARKER}.** This installation writes the graph to
`.graphify/`, never `graphify-out/`. The directory name comes from the
`GRAPHIFY_OUT` env var, which graphify reads **once at import time**
(`graphify/paths.py`) — there is **no CLI flag** for it. Therefore:

- Set it before **every** `graphify ...` CLI call in the same shell block:
  `export GRAPHIFY_OUT=.graphify` (or prefix inline:
  `GRAPHIFY_OUT=.graphify graphify update .`).
- If a repo has `scripts/graph.sh`, prefer it — it sets the variable for you.
- A bare `graphify ...` call does **not** corrupt anything: read commands
  (`query`, `path`, `explain`, `export`) fail loudly with
  `graph not found: graphify-out/graph.json`; write commands
  (`update`, `cluster-only`) would rebuild into a stray `graphify-out/`.
  Either way the graph you mean is never touched — but always prefix, so the
  run succeeds on the first try.
"""
# Subperintah yang membaca/menulis graf dan karenanya butuh GRAPHIFY_OUT.
SUBCOMMANDS = (
    "export|query|path|explain|update|cluster-only|label|benchmark|"
    "extract|merge-graphs|clone|hook|claude|save-result"
)
CMD_RE = re.compile(rf"^graphify ({SUBCOMMANDS})\b")
PREFIX = "GRAPHIFY_OUT=.graphify "

ANCHOR = "## What You Must Do When Invoked"


def find_skill_dirs() -> list[Path]:
    """Semua direktori skill graphify yang terpasang."""
    home = Path.home()
    found: list[Path] = []
    candidates = [home / ".hermes" / "skills" / "graphify"]
    profiles = home / ".hermes" / "profiles"
    if profiles.is_dir():
        candidates += sorted(profiles.glob("*/skills/graphify"))
    for c in candidates:
        if (c / "SKILL.md").is_file():
            found.append(c)
    return found


def patch_text(text: str) -> tuple[str, bool]:
    """Terapkan semua perbaikan. Kembalikan (teks_baru, berubah).

    Idempoten: blok peringatan disimpan lalu dikembalikan **apa adanya**, bukan
    diganti konstanta, supaya menjalankan ulang tidak menghasilkan diff palsu.
    """
    # 1. Lindungi blok peringatan — ia memang menyebut `graphify-out/` sebagai
    #    nama lama yang harus dihindari, jadi tidak boleh ikut diganti.
    guard = "\x00MANDATORY_BLOCK\x00"
    saved = None
    if MARKER in text:
        start = text.index("**" + MARKER)
        end = text.index("\n\n", start)
        saved = text[start:end]
        text = text[:start] + guard + text[end:]

    # 2. Nama direktori keluaran.
    text = text.replace("graphify-out", ".graphify")

    # 3. Sisipkan blok instruksi wajib bila belum ada.
    if saved is None and ANCHOR in text:
        text = text.replace(ANCHOR + "\n", ANCHOR + "\n\n" + MANDATORY_BLOCK, 1)

    # 4. Kembalikan blok peringatan persis seperti semula.
    if saved is not None:
        text = text.replace(guard, saved)

    # 5. Prefix GRAPHIFY_OUT pada baris perintah CLI.
    out: list[str] = []
    for line in text.split("\n"):
        if CMD_RE.match(line) and not line.startswith(PREFIX):
            line = PREFIX + line
        out.append(line)

    new = "\n".join(out)
    return new, new != text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--check",
        action="store_true",
        help="jangan tulis apa pun; exit 1 bila ada salinan yang belum dipatch",
    )
    args = ap.parse_args()

    dirs = find_skill_dirs()
    if not dirs:
        print("Tidak ada skill graphify terpasang.", file=sys.stderr)
        return 2

    stale = 0
    for skill in dirs:
        files = [skill / "SKILL.md", *sorted((skill / "references").glob("*.md"))]
        for f in files:
            if not f.is_file():
                continue
            old = f.read_text(encoding="utf-8")
            new, changed = patch_text(old)
            if not changed:
                continue
            stale += 1
            if args.check:
                print(f"BASI   {f}")
            else:
                f.write_text(new, encoding="utf-8")
                print(f"PATCH  {f}")

    if args.check and stale:
        print(
            f"\n{stale} file belum dipatch. Jalankan tanpa --check untuk memperbaiki.",
            file=sys.stderr,
        )
        return 1

    print(
        "Aman: skill graphify sudah menulis ke .graphify/"
        if not stale
        else f"\nSelesai: {stale} file dipatch."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
