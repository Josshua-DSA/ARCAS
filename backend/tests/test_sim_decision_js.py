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


# ---------------- bukti historis: sentimen x harga ----------------

HARI = ["2026-01-0%d" % i for i in range(1, 9)]
NAIK = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0]


def _jalan_bukti(sentiments, prices, arah, horizon):
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(JS)!r}, 'utf8');
const ctx = {{ window: {{}} }};
vm.createContext(ctx);
vm.runInContext(src, ctx);
const r = ctx.window.ARCAS.hitungBukti(
  {json.dumps(sentiments)}, {json.dumps(prices)}, {json.dumps(arah)}, {horizon});
process.stdout.write(JSON.stringify(r));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def _harga(nilai):
    return [{"date": d, "close": c} for d, c in zip(HARI, nilai)]


def _sentimen(pasangan):
    return [{"date": d, "score_mean": s} for d, s in pasangan]


def test_bukti_menghitung_hit_rate_arah_naik():
    """Harga naik monoton: setiap kejadian bersentimen positif adalah 'kena'."""
    s = _sentimen([("2026-01-01", 0.5), ("2026-01-03", 0.6), ("2026-01-05", 0.7)])
    r = _jalan_bukti(s, _harga(NAIK), "naik", 3)
    assert r["n"] == 3
    assert r["hit_rate"] == 1.0
    assert r["rata2"] > 0


def test_bukti_melewati_tanggal_tanpa_pasangan_di_ekor():
    """Tiga hari terakhir tidak punya T+3.

    Kalau dianggap return 0, hit_rate ikut tercemar dan n membengkak.
    """
    s = _sentimen([("2026-01-06", 0.9), ("2026-01-07", 0.9), ("2026-01-08", 0.9)])
    r = _jalan_bukti(s, _harga(NAIK), "naik", 3)
    assert r["n"] == 0
    assert r["hit_rate"] is None


def test_bukti_arah_turun_hanya_menghitung_skor_negatif():
    turun = [100.0, 99.0, 98.0, 97.0, 96.0, 95.0, 94.0, 93.0]
    s = _sentimen([("2026-01-01", -0.5), ("2026-01-02", 0.9), ("2026-01-03", -0.8)])
    r = _jalan_bukti(s, _harga(turun), "turun", 3)
    assert r["n"] == 2  # 01-02 positif, tidak ikut dihitung
    assert r["hit_rate"] == 1.0
    assert r["rata2"] < 0


def test_bukti_skor_di_bawah_ambang_diabaikan():
    s = _sentimen([("2026-01-01", 0.29), ("2026-01-02", 0.3)])
    r = _jalan_bukti(s, _harga(NAIK), "naik", 1)
    assert r["n"] == 1


def test_bukti_tanpa_sentimen_sama_sekali():
    r = _jalan_bukti([], _harga(NAIK), "naik", 1)
    assert r["n"] == 0
    assert r["hit_rate"] is None


# ---------------- keputusan gabungan: persona x bukti ----------------

PERSONA_BELI = [
    {"stance": "buy", "strength": 1.0},
    {"stance": "buy", "strength": 1.0},
    {"stance": "buy", "strength": 0.9},
    {"stance": "hold", "strength": 0.2},
    {"stance": "buy", "strength": 1.0},
]


def _jalan_keputusan(
    stances, confidence, warnings, arah, bukti, persentil=None
):
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(JS)!r}, 'utf8');
const ctx = {{ window: {{}} }};
vm.createContext(ctx);
vm.runInContext(src, ctx);
const r = ctx.window.ARCAS.keputusanBerita({{
  stances: {json.dumps(stances)},
  confidence: {confidence},
  warnings: {json.dumps(warnings or [])},
  arah: {json.dumps(arah)},
  bukti: {json.dumps(bukti)},
  persentil: {json.dumps(persentil)}
}});
process.stdout.write(JSON.stringify(r));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def test_bukti_tipis_mengikuti_persona():
    """XAU nyata: n=12 < 15. Persona beli, bukti tidak boleh membalik."""
    r = _jalan_keputusan(
        PERSONA_BELI, 0.99, [], "naik",
        {"T1": {"n": 12, "hit_rate": 0.33, "rata2": -0.0035},
         "T3": {"n": 12, "hit_rate": 0.33, "rata2": -0.0069}},
    )
    assert r["keputusan"] == "beli"
    assert r["label"] == "bukti tipis"
    assert r["n"] == 12


def test_bukti_kuat_membalik_persona_jadi_jual():
    """Sell on news: berita bagus tapi historisnya turun, n cukup."""
    r = _jalan_keputusan(
        PERSONA_BELI, 0.99, [], "naik",
        {"T1": {"n": 40, "hit_rate": 0.35, "rata2": -0.002},
         "T3": {"n": 40, "hit_rate": 0.33, "rata2": -0.007}},
    )
    assert r["keputusan"] == "jual"
    assert r["label"] == "sell on news"


def test_bukti_kuat_searah_persona_tetap_beli():
    r = _jalan_keputusan(
        PERSONA_BELI, 0.99, [], "naik",
        {"T1": {"n": 40, "hit_rate": 0.62, "rata2": 0.004},
         "T3": {"n": 40, "hit_rate": 0.60, "rata2": 0.008}},
    )
    assert r["keputusan"] == "beli"
    assert r["label"] == "buy on news"


def test_bukti_kuat_arah_turun_membalik_jadi_beli():
    """Berita buruk tapi historisnya justru naik = buy on bad news."""
    r = _jalan_keputusan(
        PERSONA_BELI, 0.99, [], "turun",
        {"T1": {"n": 30, "hit_rate": 0.40, "rata2": 0.002},
         "T3": {"n": 30, "hit_rate": 0.38, "rata2": 0.005}},
    )
    assert r["keputusan"] == "beli"
    assert r["label"] == "buy on news"


def test_hit_rate_di_zona_netral_tanpa_keunggulan():
    r = _jalan_keputusan(
        PERSONA_BELI, 0.99, [], "naik",
        {"T1": {"n": 40, "hit_rate": 0.50, "rata2": 0.0},
         "T3": {"n": 40, "hit_rate": 0.51, "rata2": 0.0001}},
    )
    assert r["keputusan"] == "tahan"
    assert r["label"] == "tanpa keunggulan"


def test_keyakinan_rendah_tetap_tidak_ada_sinyal():
    r = _jalan_keputusan(
        PERSONA_BELI, 0.07,
        ["Keyakinan 0.07 di bawah ambang 0.35; anggap sinyal ini lemah."],
        "naik",
        {"T1": {"n": 40, "hit_rate": 0.62, "rata2": 0.004},
         "T3": {"n": 40, "hit_rate": 0.60, "rata2": 0.008}},
    )
    assert r["keputusan"] == "tidak_ada_sinyal"


def test_catatan_puncak_hanya_keterangan():
    """Persentil tinggi tidak boleh mengubah keputusan, hanya menambah catatan."""
    bawah = _jalan_keputusan(
        PERSONA_BELI, 0.99, [], "naik",
        {"T1": {"n": 40, "hit_rate": 0.62, "rata2": 0.004},
         "T3": {"n": 40, "hit_rate": 0.60, "rata2": 0.008}}, 0.95)
    assert bawah["keputusan"] == "beli"
    assert bawah["catatan"] == "harga sudah di puncak 20 hari"
