"""Kartu ketiga di hero ikhtisar: cakupan berita pada rentang yang dipilih.

Kartu 1 = perubahan harga, kartu 2 = hari negatif. Kartu ketiga tidak
mengulang keduanya; ia mengukur berapa hari bursa yang benar-benar punya
berita, supaya pembaca tahu seberapa tebal dasar dua kartu sebelumnya.
Hari tanpa berita BUKAN nol sentimen, jadi dihitung terpisah.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path("frontend/GUI/src/js/pages/overview.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node tidak tersedia")


def _cakupan(sentiments, hari_bursa=None):
    arg2 = "" if hari_bursa is None else f", {hari_bursa}"
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(JS)!r}, 'utf8');
const A = {{
  esc: s => String(s),
  state: {{ target: 'XAU', days: 90 }},
  $: () => null,
  metaFor: () => ({{ name: 'Emas' }}),
  rapikanKeHariBursa: () => ({{ tanggal: [], tutup: [], skor: [] }}),
  showState: () => {{}},
  boot: () => {{}},
}};
const ctx = {{ window: {{ ARCAS: A }}, document: {{ getElementById: () => null }}, console }};
vm.createContext(ctx);
vm.runInContext(src, ctx);
process.stdout.write(JSON.stringify(vm.runInContext(
  'window.ARCAS.__ujiCakupan({json.dumps(sentiments)}{arg2})', ctx)));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_hari_berita_dihitung_dari_yang_punya_artikel() -> None:
    s = [
        {"date": "2026-11-03", "score_mean": 0.2, "n_articles": 3},
        {"date": "2026-11-05", "score_mean": -0.4, "n_articles": 1},
        {"date": "2026-11-06", "score_mean": None, "n_articles": 0},
    ]
    hasil = _cakupan(s)
    assert hasil["hariBerita"] == 2
    assert hasil["totalArtikel"] == 4


def test_hari_tanpa_artikel_bukan_hari_berita() -> None:
    """score_mean null tidak dihitung sebagai hari berita."""
    hasil = _cakupan([{"date": "2026-11-03", "score_mean": None, "n_articles": 0}])
    assert hasil["hariBerita"] == 0
    assert hasil["totalArtikel"] == 0


def test_cakupan_memakai_jumlah_hari_bursa_bila_diberi() -> None:
    """5 hari bursa, 2 punya berita -> 2 dari 5 (40%)."""
    s = [
        {"date": "2026-11-03", "score_mean": 0.2, "n_articles": 3},
        {"date": "2026-11-05", "score_mean": -0.4, "n_articles": 1},
    ]
    hasil = _cakupan(s, hari_bursa=5)
    assert hasil["hariBerita"] == 2
    assert hasil["hariBursa"] == 5
    assert hasil["persen"] == 40.0


def test_tanpa_hari_bursa_persen_null_bukan_nol() -> None:
    """Pembagi tidak diketahui -> persen null, bukan 0% yang menyesatkan."""
    hasil = _cakupan([{"date": "2026-11-03", "score_mean": 0.2, "n_articles": 1}])
    assert hasil["persen"] is None
