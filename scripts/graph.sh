#!/usr/bin/env bash
# Wrapper graphify untuk repo ini.
#
# `GRAPHIFY_OUT` dibaca SEKALI saat proses python mulai (graphify/paths.py).
# Tidak ada flag CLI untuk menggantinya, jadi tanpa wrapper setiap pemanggilan
# harus menuliskan `GRAPHIFY_OUT=.graphify graphify ...` — mudah lupa, dan
# akibatnya graf ditulis ke `graphify-out/` lagi (dua direktori, dua kebenaran).
#
# Pakai:
#   ./scripts/graph.sh update .          # ekstraksi AST (gratis, tanpa LLM)
#   ./scripts/graph.sh cluster-only .    # regenerasi GRAPH_REPORT.md + graph.html
#   ./scripts/graph.sh explain "ModelRouter"
#   ./scripts/graph.sh path "A" "B"
#
# Semua argumen diteruskan apa adanya ke graphify.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export GRAPHIFY_OUT=".graphify"

if ! command -v graphify >/dev/null 2>&1; then
  echo "graphify tidak ditemukan di PATH." >&2
  echo "Pasang: pipx install graphifyy" >&2
  exit 127
fi

cd "$REPO_ROOT"
exec graphify "$@"
