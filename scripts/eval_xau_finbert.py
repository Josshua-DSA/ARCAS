"""Pembungkus kompatibilitas: evaluasi FinBERT-EMAS.

Logika sebenarnya tinggal di `model/xau/evaluation/evaluate.py` agar artefak
evaluasi dan kodenya berada di satu tempat. Berkas ini dipertahankan supaya
perintah lama tetap bekerja:

    python -m scripts.eval_xau_finbert

Padanan langsungnya:

    python -m model.xau.evaluation.evaluate
"""

from __future__ import annotations

from model.xau.evaluation.evaluate import ROOT, evaluate, main

__all__ = ["ROOT", "evaluate", "main"]

if __name__ == "__main__":
    main()
