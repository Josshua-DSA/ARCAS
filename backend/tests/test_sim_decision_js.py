"""Uji agregasi stance di klien tanpa browser.

Fungsi ini menentukan keputusan yang dilihat pengguna, jadi harus diuji.
Node dipakai karena logikanya memang hidup di JS; kalau node tidak ada,
tes di-skip supaya CI tanpa node tidak merah palsu.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path("frontend/GUI/src/js/sim-decision.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node tidak tersedia")


def _jalan(stances, confidence, warnings=None):
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(JS)!r}, 'utf8');
const ctx = {{ window: {{}} }};
vm.createContext(ctx);
vm.runInContext(src, ctx);
const r = ctx.window.ARCAS.agregasiStance(
  {json.dumps(stances)}, {confidence}, {json.dumps(warnings or [])});
process.stdout.write(JSON.stringify(r));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def test_bullish_kuat_jadi_beli():
    stances = [
        {"stance": "buy", "strength": 1.0},
        {"stance": "buy", "strength": 1.0},
        {"stance": "buy", "strength": 0.986},
        {"stance": "hold", "strength": 0.219},
        {"stance": "buy", "strength": 1.0},
    ]
    r = _jalan(stances, 0.993)
    assert r["keputusan"] == "beli"
    assert r["skor"] > 0.5


def test_keyakinan_rendah_tidak_memaksa_hold():
    """Semua persona "hold" dengan keyakinan 0.07 bukan sinyal TAHAN.

    Ini kasus nyata: berita lemah menghasilkan 5x hold. Menampilkan "TAHAN"
    berarti menyatakan pasar netral padahal modelnya hanya tidak yakin.
    """
    stances = [
        {"stance": "hold", "strength": 0.005},
        {"stance": "hold", "strength": 0.014},
        {"stance": "hold", "strength": 0.004},
        {"stance": "hold", "strength": 0.001},
        {"stance": "hold", "strength": 0.006},
    ]
    r = _jalan(
        stances,
        0.065,
        ["Keyakinan 0.07 di bawah ambang 0.35; anggap sinyal ini lemah."],
    )
    assert r["keputusan"] == "tidak_ada_sinyal"
    assert r["ambang_keyakinan"] == 0.35


def test_bearish_jadi_jual():
    stances = [{"stance": "sell", "strength": 0.9}] * 4 + [
        {"stance": "hold", "strength": 0.1}
    ]
    assert _jalan(stances, 0.8)["keputusan"] == "jual"


def test_stance_kosong_tidak_melempar():
    r = _jalan([], 0.9)
    assert r["keputusan"] == "tidak_ada_sinyal"
    assert r["jumlah_persona"] == 0


def test_ambang_dibaca_dari_warnings():
    stances = [{"stance": "buy", "strength": 0.2}] * 5
    r = _jalan(
        stances, 0.40, ["Keyakinan 0.40 di bawah ambang 0.55; anggap sinyal ini lemah."]
    )
    assert r["ambang_keyakinan"] == 0.55
    assert r["keputusan"] == "tidak_ada_sinyal"


def test_halaman_tidak_lagi_merender_stance():
    """Stance dihapus dari halaman; datanya tetap dikirim server.

    Dijaga di sini supaya perubahan backend yang menghidupkan lagi blok itu
    tidak lolos tanpa disadari.
    """
    src = Path("frontend/GUI/src/js/pages/simulations.js").read_text(encoding="utf-8")
    assert "s-stance-title" not in src
    assert "Sudut pandang lima persona" not in src


def test_halaman_merender_dua_kartu():
    src = Path("frontend/GUI/src/js/pages/simulations.js").read_text(encoding="utf-8")
    assert "s-card-backtest" in src
    assert "s-card-decision" in src
