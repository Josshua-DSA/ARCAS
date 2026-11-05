"""Uji perapian daftar uji statistik di halaman riset, tanpa browser.

Dua cacat nyata yang dikunci di sini:

1. `stat_results` menyimpan baris kembar persis (XAU: 28 baris, 24 unik).
   Tanpa dedup, tabel menampilkan uji yang sama dua kali dan pembaca
   mengira rangkaiannya lebih panjang dari kenyataan.
2. Urutan baris mengikuti urutan jenis uji, bukan kekuatan bukti. Di 28 baris
   mono 10px, dua baris signifikan tenggelam di tengah.

Node dipakai karena logikanya hidup di JS; kalau node tidak ada, tes di-skip
supaya CI tanpa node tidak merah palsu.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path("frontend/GUI/src/js/pages/research.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node tidak tersedia")

HARNESS = """
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({js!r}, 'utf8');
const noop = function () {{}};
const ctx = {{
  window: {{ ARCAS: {{
    esc: function (s) {{ return String(s == null ? '' : s); }},
    fmt: function (s) {{ return String(s); }},
    showState: noop, testLabel: function (t) {{ return t; }},
    api: noop, boot: noop, localISO: noop,
    state: {{ target: 'XAU' }},
  }} }},
  document: {{
    getElementById: function () {{ return null; }},
    querySelectorAll: function () {{ return []; }},
    addEventListener: noop,
  }},
}};
vm.createContext(ctx);
vm.runInContext(src, ctx);
const A = ctx.window.ARCAS;
process.stdout.write(JSON.stringify(A.{fn}({arg})));
"""


def _panggil(fn, arg):
    skrip = HARNESS.format(js=str(JS), fn=fn, arg=json.dumps(arg))
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def _baris(**kw):
    """Satu baris stat_results dengan nilai bawaan yang wajar."""
    dasar = {
        "test": "ols",
        "market_metric": "close",
        "lag": 0,
        "estimate": 0.01,
        "p_value": 0.5,
        "p_adjusted": 0.5,
        "n_obs": 40,
        "ci_low": None,
        "ci_high": None,
    }
    dasar.update(kw)
    return dasar


# ---------------- dedupUji ----------------

def test_baris_kembar_persis_dibuang():
    """XAU punya 4 pasang baris identik; tabel hanya boleh menampilkan satu."""
    rows = [
        _baris(lag=4, estimate=-0.007442, p_adjusted=0.004111, n_obs=42),
        _baris(lag=4, estimate=-0.007442, p_adjusted=0.004111, n_obs=42),
        _baris(lag=0, estimate=-0.009408, p_adjusted=0.465972, n_obs=10),
        _baris(lag=0, estimate=-0.009408, p_adjusted=0.465972, n_obs=10),
    ]
    hasil = _panggil("dedupUji", rows)
    assert len(hasil) == 2


def test_baris_beda_satu_kolom_tetap_dua():
    """Lag berbeda adalah uji berbeda. Dedup tidak boleh menelannya."""
    rows = [
        _baris(lag=1, estimate=0.02, p_adjusted=0.3),
        _baris(lag=2, estimate=0.02, p_adjusted=0.3),
    ]
    assert len(_panggil("dedupUji", rows)) == 2


def test_jenis_uji_beda_tetap_dua():
    rows = [
        _baris(test="ols", lag=None, estimate=0.5, p_adjusted=0.01),
        _baris(test="event_study", lag=None, estimate=0.5, p_adjusted=0.01),
    ]
    assert len(_panggil("dedupUji", rows)) == 2


def test_p_adjusted_null_tidak_dianggap_sama_dengan_nol():
    """Baris tanpa p_adj harus tetap terpisah dari baris ber-p_adj 0."""
    rows = [
        _baris(lag=1, p_adjusted=None),
        _baris(lag=1, p_adjusted=0.0),
    ]
    assert len(_panggil("dedupUji", rows)) == 2


def test_dedup_kosong_aman():
    assert _panggil("dedupUji", []) == []


# ---------------- urutUji ----------------

def test_baris_signifikan_naik_ke_atas():
    rows = [
        _baris(test="granger", lag=1, p_adjusted=0.80),
        _baris(test="ols", lag=4, p_adjusted=0.004),
        _baris(test="ols", lag=2, p_adjusted=0.30),
    ]
    hasil = _panggil("urutUji", rows)
    assert [r["p_adjusted"] for r in hasil] == [0.004, 0.30, 0.80]


def test_sesama_signifikan_diurut_p_adj_naik():
    rows = [
        _baris(lag=1, p_adjusted=0.03),
        _baris(lag=2, p_adjusted=0.001),
        _baris(lag=3, p_adjusted=0.02),
    ]
    hasil = _panggil("urutUji", rows)
    assert [r["p_adjusted"] for r in hasil] == [0.001, 0.02, 0.03]


def test_tanpa_p_adj_selalu_di_bawah():
    """Baris tanpa p_adj tidak punya bukti untuk ditonjolkan."""
    rows = [
        _baris(lag=1, p_adjusted=None),
        _baris(lag=2, p_adjusted=0.9),
    ]
    hasil = _panggil("urutUji", rows)
    assert hasil[0]["p_adjusted"] == 0.9
    assert hasil[-1]["p_adjusted"] is None


def test_sig_dihitung_pada_ambang_lima_persen_walau_dibulatkan_sama():
    """0.049 dan 0.051 tampil sama sebagai 0.05 di UI, tapi beda status."""
    rows = [
        _baris(lag=1, p_adjusted=0.051),
        _baris(lag=2, p_adjusted=0.049),
    ]
    hasil = _panggil("urutUji", rows)
    assert hasil[0]["p_adjusted"] == 0.049


def test_urutan_stabil_untuk_baris_setara():
    """Dua baris dengan p_adj dan lag sama tidak boleh bertukar posisi."""
    rows = [
        _baris(test="granger", lag=1, p_adjusted=0.2),
        _baris(test="ols", lag=1, p_adjusted=0.2),
    ]
    a = _panggil("urutUji", rows)
    b = _panggil("urutUji", rows)
    assert a == b


def test_urut_tidak_mengubah_jumlah_baris():
    rows = [_baris(lag=i, p_adjusted=0.1 * i) for i in range(5)]
    assert len(_panggil("urutUji", rows)) == 5
