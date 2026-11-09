"""Tiap kartu simulasi punya id stabil dan data-target.

Dua kartu dirender per giliran (backtesting + keputusan). Tanpa id, kartu
tidak bisa ditandai maupun diuji dari luar. Id harus unik: body kartu
keputusan sudah memakai pola `sim-N-keputusan`, jadi id section tidak boleh
sama -- kalau bentrok, getElementById mengembalikan section dan render isi
menimpa header kartu.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path("frontend/GUI/src/js/pages/simulations.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node tidak tersedia")


def _kartu(id_kartu="sim-3", target="XAU"):
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(JS)!r}, 'utf8');
const A = {{
  esc: s => String(s),
  state: {{ target: 'XAU', days: 90 }},
  $: () => null,
  metaFor: () => ({{ name: 'Emas' }}),
  fmt: v => String(v),
  boot: () => {{}},
}};
const ctx = {{ window: {{ ARCAS: A }}, document: {{ getElementById: () => null }}, console }};
vm.createContext(ctx);
vm.runInContext(src, ctx);
process.stdout.write(JSON.stringify(
  vm.runInContext('window.ARCAS.__ujiKartu({json.dumps(id_kartu)}, {json.dumps(target)})', ctx)));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0, out.stderr
    h = json.loads(out.stdout)
    return h


def test_section_punya_id_stabil() -> None:
    h = _kartu()
    assert "id='sim-3-backtest'" in h["backtest"]
    assert "id='sim-3-keputusan'" in h["keputusan"]


def test_section_punya_satu_data_target() -> None:
    h = _kartu()
    assert h["backtest"].count("data-target") == 1
    assert h["keputusan"].count("data-target") == 1


def test_data_target_mengikuti_target_giliran() -> None:
    assert "data-target='SPX'" in _kartu("sim-7", "SPX")["backtest"]
    assert "data-target='SPX'" in _kartu("sim-7", "SPX")["keputusan"]


def test_id_body_keputusan_tidak_bentrok_dengan_section() -> None:
    """Id section dan id body tidak boleh sama."""
    h = _kartu()
    assert "id='sim-3-keputusan-isi'" in h["keputusan"]


def test_semua_id_dalam_satu_kartu_unik() -> None:
    h = _kartu()
    ids = re.findall(r"id='([^']+)'", h["backtest"] + h["keputusan"])
    assert len(ids) == len(set(ids))
