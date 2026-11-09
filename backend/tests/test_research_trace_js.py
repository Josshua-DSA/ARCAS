"""Jejak harga T+n harus membedakan dua sebab kosong yang berbeda artinya.

- "sesi belum terjadi" (T+3 melewati ujung deret harga karena harganya memang
  belum ada) -> wajar, bukan cacat data.
- "tanggal tidak di deret" (tanggal berita jatuh di luar rentang harga yang
  dimuat) -> data bolong, perlu diperiksa.

Dulu keduanya tampil sebagai teks yang sama, "di luar deret", sehingga cacat
data tidak bisa dibedakan dari sesi yang belum berjalan.
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

# Deret harga pendek: 3 hari bursa saja. idx=2 berarti T+1 sudah lewat ujung.
HARGA = ["2026-11-03", "2026-11-04", "2026-11-05"]
TUTUP = [4100.0, 4110.0, 4120.0]


def _jalankan(ekspresi: str):
    """Muat research.js di ctx minimal: cukup A.esc + A.state, tanpa DOM."""
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(JS)!r}, 'utf8');
const A = {{
  esc: s => String(s).replace(/[&<>"']/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}})[c]),
  state: {{ target: 'XAU', days: 180 }},
  $: () => null,
}};
const ctx = {{ window: {{ ARCAS: A }}, document: {{ getElementById: () => null }}, console }};
vm.createContext(ctx);
vm.runInContext(src, ctx);
process.stdout.write(JSON.stringify(vm.runInContext({json.dumps(ekspresi)}, ctx)));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, timeout=30
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def _jejak(idx: int, ada_berita: bool = True):
    return _jalankan(
        f"window.ARCAS.__ujiJejak({idx}, {json.dumps(HARGA)}, {json.dumps(TUTUP)}, {json.dumps(ada_berita)})"
    )


def test_t1_dihitung_normal_saat_data_ada() -> None:
    hasil = _jejak(0)
    assert hasil[0]["label"] == "T+1"
    assert hasil[0]["persen"] == pytest.approx((4110.0 / 4100.0 - 1) * 100)
    assert hasil[0]["tanggal"] == "2026-11-04"
    assert hasil[0]["sebab"] is None


def test_lewat_ujung_deret_disebut_sesi_belum_terjadi() -> None:
    """idx=2: T+1 pun sudah di luar deret, karena harga berhenti di 11-05."""
    hasil = _jejak(2)
    assert hasil[0]["persen"] is None
    assert hasil[0]["tanggal"] is None
    assert hasil[0]["sebab"] == "sesi belum terjadi"


def test_berita_di_luar_deret_harga_disebut_tanggal_tidak_di_deret() -> None:
    """idx=-1: tanggal berita tidak ada di deret sama sekali -> cacat data."""
    hasil = _jejak(-1)
    assert hasil[0]["persen"] is None
    assert hasil[0]["sebab"] == "tanggal tidak di deret"


def test_t3_dan_t5_mewarisi_sebab_yang_sama() -> None:
    hasil = _jejak(2)
    assert [h["label"] for h in hasil] == ["T+1", "T+3", "T+5"]
    assert all(h["sebab"] == "sesi belum terjadi" for h in hasil)


def test_dua_sebab_tidak_pernah_tertukar() -> None:
    """Sesi belum terjadi bukan cacat data; cacat data bukan sesi."""
    lewat = _jejak(2)[0]["sebab"]
    luar = _jejak(-1)[0]["sebab"]
    assert lewat != luar
