"""Generates static HTML and JSON analytical reports into outputs/."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class ReportExporter:
    """Exports system analytical snapshots and statistics."""

    def __init__(self, output_dir: Path | str = Path("outputs")):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_html_report(
        self,
        universe: list[dict],
        stats: list[dict],
        allocations: dict[str, Any],
        report_name: str = "report.html",
        universe_version: str = "2026-10-12-core3",
    ) -> Path:
        """Renders self-contained static HTML report for the 3 core targets."""
        out_file = self.output_dir / report_name
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        rows_html = "".join([
            f"<tr><td><code>{u.get('asset_id')}</code></td><td>{u.get('name')}</td><td>{u.get('track')}</td><td>{u.get('asset_class')}</td><td>{u.get('session_close')}</td></tr>"
            for u in universe
        ])

        def _fmt(value: Any, digits: int = 4) -> str:
            """Format angka untuk HTML; `None` jadi tanda pisah, bukan 'None'."""
            if value is None or value == "":
                return "&mdash;"
            if isinstance(value, (int, float)):
                return f"{value:.{digits}f}"
            return str(value)

        def _p_class(p_adj: Any) -> str:
            """Tandai signifikansi setelah koreksi BH dengan warna."""
            if not isinstance(p_adj, (int, float)):
                return ""
            if p_adj < 0.01:
                return "sig-strong"
            if p_adj < 0.05:
                return "sig"
            return ""

        stats_html = "".join([
            f"<tr class='{_p_class(r.get('p_adjusted'))}'>"
            f"<td><code>{r.get('asset_id')}</code></td>"
            f"<td>{r.get('test')}</td>"
            f"<td>{r.get('lag')}</td>"
            f"<td>{_fmt(r.get('estimate'), 5)}</td>"
            f"<td>[{_fmt(r.get('ci_low'), 5)}, {_fmt(r.get('ci_high'), 5)}]</td>"
            f"<td>{_fmt(r.get('p_value'))}</td>"
            f"<td>{_fmt(r.get('p_adjusted'))}</td>"
            f"<td>{r.get('n_obs')}</td>"
            f"</tr>"
            for r in stats
        ])
        if not stats_html:
            stats_html = (
                "<tr><td colspan='8' style='color:#d8dee9'>"
                "Belum ada hasil statistik. Jalankan <code>cli stats</code> lebih dulu."
                "</td></tr>"
            )

        html_content = f"""<!DOCTYPE html>
<html lang="id">
<head>
  <meta charset="UTF-8">
  <title>FinNews Analytical Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #2e3440; color: #eceff4; margin: 0; padding: 24px; }}
    .container {{ max-width: 1000px; margin: 0 auto; }}
    h1, h2 {{ color: #88c0d0; }}
    .card {{ background: #3b4252; border: 1px solid #4c566a; border-radius: 8px; padding: 16px; margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ padding: 8px 12px; text-align: left; border-bottom: 1px solid #4c566a; }}
    th {{ background: #434c5e; color: #81a1c1; }}
    .disclaimer {{ font-size: 0.85rem; color: #d8dee9; font-style: italic; margin-top: 24px; padding: 12px; border-left: 4px solid #ebcb8b; background: #3b4252; }}
    code {{ background: #4c566a; padding: 2px 6px; border-radius: 4px; }}
    tr.sig td {{ color: #a3be8c; }}
    tr.sig-strong td {{ color: #a3be8c; font-weight: 600; }}
    .note {{ font-size: 0.85rem; color: #d8dee9; margin-top: 8px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>FinNews Macro Sentiment Report</h1>
    <p>Dibuat: {timestamp} | Versi Skema: v0.5.0 | Universe: {universe_version} (3 target inti)</p>

    <div class="card">
      <h2>Core Locked Universe (3 Target)</h2>
      <table>
        <thead>
          <tr><th>ID</th><th>Nama</th><th>Track</th><th>Kelas</th><th>Sesi Tutup</th></tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>

    <div class="card">
      <h2>Hubungan Sentimen &harr; Pasar</h2>
      <table>
        <thead>
          <tr><th>Aset</th><th>Uji</th><th>Lag</th><th>Estimasi</th><th>CI 95%</th><th>p</th><th>p (BH)</th><th>n</th></tr>
        </thead>
        <tbody>
          {stats_html}
        </tbody>
      </table>
      <p class="note">
        p (BH) = p-value setelah koreksi Benjamini-Hochberg lintas lag.
        OLS memakai galat Newey-West (HAC). Baris hijau: p (BH) &lt; 0,05.
      </p>
    </div>

    <div class="disclaimer">
      <strong>Peringatan Risiko:</strong> Simulasi analitis ini bertujuan untuk penelitian dan edukasi semata. Bukan merupakan rekomendasi finansial atau nasihat investasi berlisensi.
    </div>
  </div>
</body>
</html>
"""
        with open(out_file, mode="w", encoding="utf-8") as f:
            f.write(html_content)

        return out_file

    def export_json_snapshot(self, data: dict, filename: str = "snapshot.json") -> Path:
        """Exports analytical JSON snapshot."""
        out_file = self.output_dir / filename
        with open(out_file, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return out_file
