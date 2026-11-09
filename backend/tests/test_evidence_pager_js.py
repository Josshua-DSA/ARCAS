"""Pager halaman bukti: 10 kartu per halaman, saringan atas SELURUH baris.

Halaman bukti sebelumnya merender 50 kartu sekaligus (14.809px, 9x halaman
lain) tanpa pager. Yang salah bukan jumlah yang dimuat, tapi tidak adanya
pemotong render: saringan kata kunci dan arah harus tetap melihat seluruh
populasi, sebab memotong data akan membuat saringan kehilangan hasil.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path("frontend/GUI/src/js/pages/evidence.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node tidak tersedia")


def _jalankan(ekspresi: str):
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(JS)!r}, 'utf8');
const el = () => ({{ addEventListener: () => {{}}, value: '',
  innerHTML: '', textContent: '', hidden: false, click: () => {{}} }});
const A = {{
  esc: s => String(s),
  $: el,
  showState: () => {{}},
  boot: () => {{}},
}};
const ctx = {{ window: {{ ARCAS: A }}, document: {{ getElementById: el,
  querySelectorAll: () => [] }}, console }};
vm.createContext(ctx);
vm.runInContext(src, ctx);
process.stdout.write(JSON.stringify(vm.runInContext({json.dumps(ekspresi)}, ctx)));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _baris(n: int):
    arah = ["bearish", "bullish", "neutral"]
    return [
        {"article_id": f"a{i}", "title": f"Judul {i}", "direction": arah[i % 3],
         "source": "Reuters"}
        for i in range(n)
    ]


def test_sepuluh_per_halaman_dan_lima_halaman() -> None:
    hasil = _jalankan(
        f"window.ARCAS.__ujiPotong({json.dumps(_baris(50))}, 1, 10)"
    )
    assert len(hasil["baris"]) == 10
    assert hasil["jumlahHalaman"] == 5
    assert hasil["total"] == 50


def test_halaman_terakhir_berisi_sisanya() -> None:
    hasil = _jalankan(
        f"window.ARCAS.__ujiPotong({json.dumps(_baris(50))}, 5, 10)"
    )
    assert len(hasil["baris"]) == 10
    assert hasil["baris"][0]["article_id"] == "a40"


def test_data_lima_belas_jadi_dua_halaman_lima_ekor() -> None:
    hasil = _jalankan(
        f"window.ARCAS.__ujiPotong({json.dumps(_baris(15))}, 2, 10)"
    )
    assert hasil["jumlahHalaman"] == 2
    assert len(hasil["baris"]) == 5


def test_saringan_arah_melihat_seluruh_populasi_bukan_satu_halaman() -> None:
    """Arah bearish tersebar di 50 baris; saringan harus menemukan semuanya."""
    hasil = _jalankan(
        f"window.ARCAS.__ujiSaring({json.dumps(_baris(50))}, '', 'bearish').length"
    )
    assert hasil == 17  # i % 3 == 0 untuk i = 0..48


def test_saringan_kata_dan_arah_bergabung() -> None:
    hasil = _jalankan(
        f"window.ARCAS.__ujiSaring({json.dumps(_baris(50))}, 'Judul 4', 'neutral').length"
    )
    # "Judul 4" cocok dengan 4, 40..49 (11 baris). Neutral = i % 3 == 2,
    # jadi yang lolos hanya 41, 44, 47.
    assert hasil == 3


def test_halaman_di_luar_rentang_dipangkas_ke_terakhir() -> None:
    hasil = _jalankan(
        f"window.ARCAS.__ujiPotong({json.dumps(_baris(50))}, 99, 10)"
    )
    assert hasil["halaman"] == 5
    assert len(hasil["baris"]) == 10


def test_tanpa_baris_tetap_satu_halaman_kosong() -> None:
    hasil = _jalankan("window.ARCAS.__ujiPotong([], 1, 10)")
    assert hasil["jumlahHalaman"] == 1
    assert hasil["baris"] == []
