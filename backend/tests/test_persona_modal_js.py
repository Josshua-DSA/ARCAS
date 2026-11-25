"""Uji narasi modal Persona POV di News & Evidence (shell.js).

Memastikan kolom Alasan menampilkan narasi yang mudah dipahami per karakter
persona sekaligus menjaga jejak statistik asli dari backend, judul modal
dipotong rapi di batas kata, dan chip stance tidak patah dua baris.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SHELL_JS = Path("frontend/GUI/src/js/shell.js")
LAYOUT_CSS = Path("frontend/GUI/src/css/layout.css")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node tidak tersedia")


def _run_shell(expr: str):
    skrip = f"""
const fs = require('fs');
const vm = require('vm');
const src = fs.readFileSync({str(SHELL_JS)!r}, 'utf8');
const ctx = {{
  window: {{ location: {{ pathname: '/evidence.html', search: '' }} }},
  document: {{
    getElementById: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {{}},
    body: {{ classList: {{ add() {{}}, remove() {{}} }}, appendChild() {{}} }}
  }},
  URLSearchParams,
  console
}};
vm.createContext(ctx);
vm.runInContext(src, ctx);
const A = ctx.window.ARCAS;
const hasil = ({expr});
process.stdout.write(JSON.stringify(hasil));
"""
    out = subprocess.run(
        [NODE or "node", "-e", skrip], capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def test_lima_persona_hold_punya_narasi_unik_dan_jejak_statistik() -> None:
    views = [
        {
            "persona_id": "retail",
            "target": "XAU",
            "stance": "hold",
            "raw_value": -0.07,
            "confidence": 0.71,
            "rationale": "Intensitas sinyal (0.07) berada di dalam rentang netral.",
        },
        {
            "persona_id": "day_trader",
            "target": "XAU",
            "stance": "hold",
            "raw_value": -0.09,
            "confidence": 0.71,
            "rationale": "Intensitas sinyal (0.09) berada di dalam rentang netral.",
        },
        {
            "persona_id": "fund_manager",
            "target": "XAU",
            "stance": "hold",
            "raw_value": -0.06,
            "confidence": 0.71,
            "rationale": "Intensitas sinyal (0.06) berada di dalam rentang netral.",
        },
        {
            "persona_id": "pension",
            "target": "XAU",
            "stance": "hold",
            "raw_value": -0.02,
            "confidence": 0.71,
            "rationale": "Tingkat keyakinan (0.71) di bawah batas minimum (0.75).",
        },
        {
            "persona_id": "risk_manager",
            "target": "XAU",
            "stance": "hold",
            "raw_value": -0.09,
            "confidence": 0.71,
            "rationale": "Intensitas sinyal (0.09) berada di dalam rentang netral.",
        },
    ]
    res = _run_shell(f"({json.dumps(views)}).map(v => A.alasanPersona(v))")
    narasi = [r["narasi"] for r in res]
    assert len(set(narasi)) == 5, "kelima persona harus memiliki narasi berbeda"
    assert all(n.startswith("Akan hold karena") for n in narasi)
    # Baris netral memuat tanda arah (-0.07) + jejak asli backend
    assert "-0.07" in res[0]["stat"]
    assert "rentang netral" in res[0]["stat"]
    # Baris pension memuat jejak batas minimum keyakinan
    assert "0.75" in res[3]["stat"]
    assert "kepastian berita" in res[3]["narasi"]


def test_buy_dan_sell_sesuai_stance_dan_menjaga_stat() -> None:
    buy_v = {
        "persona_id": "day_trader",
        "target": "SPX",
        "stance": "buy",
        "raw_value": 0.42,
        "confidence": 0.88,
        "rationale": "Sinyal bullish terkonfirmasi melampaui ambang (+0.42 >= 0.15).",
    }
    sell_v = {
        "persona_id": "risk_manager",
        "target": "XAU",
        "stance": "sell",
        "raw_value": -0.51,
        "confidence": 0.85,
        "rationale": "Sinyal risiko negatif terpicu dengan penalti mitigasi (-0.51 <= -0.20).",
    }
    r_buy = _run_shell(f"A.alasanPersona({json.dumps(buy_v)})")
    r_sell = _run_shell(f"A.alasanPersona({json.dumps(sell_v)})")
    assert r_buy["narasi"].startswith("Akan buy karena")
    assert "S&P 500" in r_buy["narasi"]
    assert "+0.42 >= 0.15" in r_buy["stat"]
    assert r_sell["narasi"].startswith("Akan sell/lindung nilai karena")
    assert "Emas" in r_sell["narasi"]
    assert "-0.51 <= -0.20" in r_sell["stat"]


def test_demo_offline_tidak_mengarang_narasi() -> None:
    demo = {
        "persona_id": "retail",
        "target": "XAU",
        "stance": "buy",
        "raw_value": 0.2,
        "confidence": 0.6,
        "params_version": "demo",
        "rationale": "Ilustrasi lokal: API persona tidak terjangkau.",
    }
    r = _run_shell(f"A.alasanPersona({json.dumps(demo)})")
    assert r["narasi"] == demo["rationale"]
    assert r["stat"] == ""


def test_judul_singkat_potong_di_batas_kata() -> None:
    panjang = "During Wall Street's worst week in over a year, we put money to work. What we're buying"
    pendek = "Gold edges higher ahead of Fed"
    res = _run_shell(
        f"[A.judulSingkat({panjang!r}, 52), A.judulSingkat({pendek!r}, 52)]"
    )
    assert res[0].endswith("...")
    assert len(res[0]) <= 55
    assert "money to work" not in res[0]
    assert res[1] == pendek


def test_css_chip_modal_tidak_patah_baris() -> None:
    css = LAYOUT_CSS.read_text(encoding="utf-8")
    assert "#personaModal .chip{white-space:nowrap}" in css
