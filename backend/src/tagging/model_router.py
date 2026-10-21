"""Two-stage cascade router: news text -> specialist model id.

Tahap 1: petunjuk sumber + kamus kata kunci (deterministik, tanpa model).
Tahap 2: bukti log-odds domain per token (tangkap sinonim & istilah implisit).
Fallback: baseline_tfidf bila kedua tahap tidak yakin.

Bobot tahap 2 dibangun oleh scripts/build_router_centroids.py dari dataset
benchmark; konfigurasi di data/router_config.yaml.

Tokenizer di modul ini adalah sumber kebenaran bersama: builder wajib memakai
`tokens()` yang sama, kalau tidak bobot dan inferensi tidak sepadan.

Tahap 2 memakai aturan bukti, bukan rata-rata buta: minimal `min_votes` token
dengan |z| >= `z_min` yang searah. Rata-rata saja pernah merutekan berita cuaca
ke FOMC hanya karena satu kata kebetulan.
"""

import json
import re
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_CONFIG = Path("data/router_config.yaml")
DEFAULT_WEIGHTS = Path("model/weights/router_centroids.json")

_TOKEN = re.compile(r"[a-z0-9][a-z0-9'&.-]*")

# Fungsi kata bahasa Inggris menguasai kedua korpus dan menenggelamkan kata isi.
STOPWORDS = frozenset("""
a an the and or but if of to in on at for with from by as is are was were be been being
that this these those it its they their them he she his her we our you your i me my
not no nor so than then there here which who whom whose what when where while about
into over under after before during between against through above below up down out
off again further once all any both each few more most other some such only own same
very can will just should now also may might must shall would could have has had do
does did done said says say according one two three new us
""".split())


def tokens(text: str) -> list[str]:
    """Lowercase token tanpa stopword. Dipakai builder dan router."""
    return [t for t in _TOKEN.findall(str(text).lower()) if t not in STOPWORDS]


class ModelRouter:
    """Routes an article to the specialist model that should score it."""

    def __init__(
        self,
        config_path: Path | str = DEFAULT_CONFIG,
        weights_path: Path | str = DEFAULT_WEIGHTS,
    ):
        cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
        self.version: str = cfg["version"]
        self.z_min: float = float(cfg["z_min"])
        self.min_votes: int = int(cfg["min_votes"])
        self.fallback: str = cfg["fallback"]
        self.sources: dict[str, list[str]] = cfg.get("sources", {})
        self.keywords: dict[str, list[str]] = cfg.get("keywords", {})

        p = Path(weights_path)
        self.weights: dict[str, float] = {}
        self.weights_version: Optional[str] = None
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            self.weights = data["weights"]
            self.weights_version = data.get("version")

    def evidence(self, text: str) -> dict[str, float]:
        """Rata-rata z dan jumlah bukti kuat per domain."""
        zs = [self.weights[t] for t in tokens(text) if t in self.weights]
        if not zs:
            return {"mean": 0.0, "gold": 0, "fomc": 0}
        return {
            "mean": sum(zs) / len(zs),
            "gold": sum(1 for z in zs if z >= self.z_min),
            "fomc": sum(1 for z in zs if z <= -self.z_min),
        }

    def route(self, text: str, source: str = "") -> tuple[list[str], str, float]:
        """Returns (model_ids, reason, score). reason: source|keyword|log_odds|fallback."""
        src = (source or "").lower()
        for model_id, hints in self.sources.items():
            if any(h in src for h in hints):
                return [model_id], "source", 1.0

        low = text.lower()
        hits: list[str] = []
        for model_id, words in self.keywords.items():
            # bentuk jamak sederhana: "rate cut" cocok dengan "rate cuts"
            if any(re.search(rf"\b{re.escape(w)}(?:s|es)?\b", low) for w in words):
                hits.append(model_id)
        if hits:
            return hits, "keyword", 1.0

        ev = self.evidence(text)
        if ev["gold"] >= self.min_votes and ev["gold"] > ev["fomc"]:
            return ["finbert_emas"], "log_odds", round(ev["mean"], 4)
        if ev["fomc"] >= self.min_votes and ev["fomc"] > ev["gold"]:
            return ["fomc_roberta"], "log_odds", round(ev["mean"], 4)

        return [self.fallback], "fallback", 0.0
