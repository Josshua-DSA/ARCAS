"""Ambang keputusan sentimen dari konfigurasi, bukan dari kode.

`RULES.md` melarang magic number: ambang, cap, bobot, dan penalti wajib
berada di config/YAML. Sebelum modul ini, kedua track menulis `0.10`
sebagai literal di kode sehingga mengubahnya menuntut edit kode dan tidak
tercatat di versi konfigurasi.

Nilai bawaan di modul ini **sama persis** dengan nilai literal yang
sebelumnya dipakai, sehingga perilaku tidak berubah bila file YAML tidak
ada (mis. saat wheel dipasang tanpa `data/`).

Berkas: `data/sentiment_config.yaml`
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("data/sentiment_config.yaml")

#: Nilai cadangan bila YAML tidak ada / tidak lengkap. Harus identik dengan
#: isi `data/sentiment_config.yaml` supaya perilaku tidak bergantung pada
#: keberadaan file.
FALLBACK: dict[str, Any] = {
    "neutral_band": 0.10,
}


def load_sentiment_config(path: Path | str | None = None) -> dict[str, Any]:
    """Muat ambang sentimen; selalu mengembalikan dict lengkap dan tervalidasi.

    Toleran terhadap file hilang atau rusak: nilai bawaan dipakai dan
    kegagalan dicatat. Model sentimen tidak boleh mati hanya karena YAML
    tidak terbaca.
    """
    cfg = dict(FALLBACK)
    p = Path(path) if path is not None else DEFAULT_CONFIG_PATH

    if not p.exists():
        return cfg

    try:
        with open(p, mode="r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Gagal membaca %s (%s); memakai ambang bawaan.", p, exc)
        return cfg

    if not isinstance(data, dict):
        logger.warning("%s bukan mapping; memakai ambang bawaan.", p)
        return cfg

    # Bentuk yang didukung: datar (`neutral_band: 0.1`) atau bersarang
    # (`decision: {neutral_band: 0.1}`). Keduanya diterima agar berkas bisa
    # dikembangkan tanpa mematahkan pemuat lama.
    section = data.get("decision")
    source = section if isinstance(section, dict) else data
    raw = source.get("neutral_band", cfg["neutral_band"])

    try:
        band = float(raw)
    except (TypeError, ValueError):
        logger.warning("neutral_band tidak numerik (%r); memakai bawaan.", raw)
        return cfg

    # Ambang negatif tidak masuk akal: skor = p_pos - p_neg ada di [-1, 1]
    # dan harus simetris terhadap nol.
    if not 0.0 <= band <= 1.0:
        logger.warning("neutral_band di luar [0, 1] (%s); memakai bawaan.", band)
        return cfg

    cfg["neutral_band"] = band
    return cfg


def neutral_band(path: Path | str | None = None) -> float:
    """Ambil satu nilai `neutral_band` siap pakai."""
    value = load_sentiment_config(path)["neutral_band"]
    return float(value)
