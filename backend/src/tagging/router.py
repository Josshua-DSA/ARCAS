"""Router for mapping news text to targets via keywords and macro themes."""

import csv
from pathlib import Path
from typing import Optional
import yaml

from backend.src.schema import Article, Basis, Direction, EvidenceSpan, TargetImpact


LOCKED_UNIVERSE = {
    "XAU", "RATE_UST", "SPX"
}


class TargetRouter:
    """Tags targets and projects macro impact from text."""

    def __init__(
        self,
        aliases_path: Path | str = Path("data/universe/aliases.csv"),
        impact_graph_path: Path | str = Path("data/impact_graph.yaml"),
    ):
        self.aliases_path = Path(aliases_path)
        self.impact_graph_path = Path(impact_graph_path)
        self.aliases: dict[str, list[str]] = {}  # asset_id -> list of alias strings
        self.impact_graph: dict[str, list[dict]] = {}  # theme -> list of targets
        self._load_configs()

    def _load_configs(self) -> None:
        if self.aliases_path.exists():
            with open(self.aliases_path, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    asset = row["asset_id"]
                    if asset in LOCKED_UNIVERSE:
                        self.aliases.setdefault(asset, []).append(row["alias"].strip().lower())

        if self.impact_graph_path.exists():
            with open(self.impact_graph_path, mode="r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.impact_graph = data.get("themes", {})

    def find_explicit_mentions(self, text: str) -> list[tuple[str, str, int, int]]:
        """
        Finds direct alias matches in text.
        Returns list of (asset_id, matched_alias, start_pos, end_pos).
        """
        lower_text = text.lower()
        matches: list[tuple[str, str, int, int]] = []

        for asset_id, alias_list in self.aliases.items():
            for alias in alias_list:
                pos = lower_text.find(alias)
                if pos != -1:
                    matches.append((asset_id, alias, pos, pos + len(alias)))
                    break  # Found match for this asset
        return matches

    def detect_themes(self, text: str) -> list[str]:
        """Simple keyword detection for macro themes in text."""
        lower = text.lower()
        active_themes: list[str] = []

        theme_keywords = {
            "rates_down": ["pangkas suku bunga", "rate cut", "pemotongan bunga", "dovish"],
            "rates_up": ["naikkan suku bunga", "rate hike", "kenaikan bunga", "hawkish"],
            "usd_up": ["dolar perkasa", "usd menguat", "dollar surges", "strong dollar"],
            "risk_off": ["gejolak pasar", "ketidakpastian global", "panic selling", "flight to safety"],
            "geopolitical_tension": ["eskalasi perang", "geopolitik", "konflik timur tengah", "sanksi dagang"],
        }

        for theme, kw_list in theme_keywords.items():
            if any(kw in lower for kw in kw_list):
                active_themes.append(theme)

        return active_themes

    def route_article(
        self, article: Article, sentiment_score: float, model_version: str = "fusion-v1"
    ) -> list[TargetImpact]:
        """
        Routes an article to target impacts via explicit mentions and macro themes.
        Strict rule: caps confidence by basis and builds evidence for explicit tags.
        """
        impacts: list[TargetImpact] = []
        full_text = f"{article.title} {article.body or ''}".strip()

        # 1. Explicit matches
        explicit_matches = self.find_explicit_mentions(full_text)
        tagged_assets = set()

        for asset_id, matched_alias, start, end in explicit_matches:
            tagged_assets.add(asset_id)
            # Direction follows sentiment score for explicit mentions
            if sentiment_score > 0.1:
                direction = Direction.BULLISH
            elif sentiment_score < -0.1:
                direction = Direction.BEARISH
            else:
                direction = Direction.NEUTRAL

            evidence = [
                EvidenceSpan(
                    quote=full_text[max(0, start - 20) : min(len(full_text), end + 40)],
                    start=start,
                    end=end,
                )
            ]

            impacts.append(
                TargetImpact(
                    article_id=article.article_id,
                    asset_id=asset_id,
                    direction=direction,
                    score=sentiment_score,
                    confidence=0.88,  # Under explicit cap 1.00
                    basis=Basis.EXPLICIT,
                    themes=[],
                    evidence=evidence,
                    flags=[],
                    model_version=model_version,
                )
            )

        # 2. Macro themes mapping via impact_graph
        themes = self.detect_themes(full_text)
        for theme in themes:
            theme_targets = self.impact_graph.get(theme, [])
            for entry in theme_targets:
                asset_id = entry.get("target")
                if not asset_id or asset_id not in LOCKED_UNIVERSE:
                    continue
                if asset_id in tagged_assets:
                    continue  # Explicit priority

                sign = entry.get("sign", 1)
                weight = entry.get("weight", 0.5)
                projected_score = sentiment_score * sign * weight

                if projected_score > 0.1:
                    direction = Direction.BULLISH
                elif projected_score < -0.1:
                    direction = Direction.BEARISH
                else:
                    direction = Direction.NEUTRAL

                impacts.append(
                    TargetImpact(
                        article_id=article.article_id,
                        asset_id=asset_id,
                        direction=direction,
                        score=max(-1.0, min(1.0, projected_score)),
                        confidence=min(0.85, 0.50 + weight * 0.35),  # Cap 0.85
                        basis=Basis.MACRO_FACTOR,
                        themes=[theme],
                        causal_path=[theme, f"{asset_id}_{direction.value}"],
                        evidence=[],
                        flags=[],
                        model_version=model_version,
                    )
                )

        return impacts
