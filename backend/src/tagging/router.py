"""Router for mapping news text to targets via keywords and macro themes."""

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import yaml

from backend.src.schema import (
    Article,
    Basis,
    Direction,
    EvidenceSpan,
    NewsHorizon,
    TargetImpact,
)

if TYPE_CHECKING:  # pragma: no cover - hanya untuk anotasi tipe
    from backend.src.tagging.model_router import ModelRouter


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

        # T-5: ambang & kalibrasi dari YAML, bukan angka ajaib di kode.
        self.config_path = Path("data/router_config.yaml")
        self.routing: dict[str, float] = {
            "direction_threshold": 0.1,
            "explicit_confidence": 0.88,
            "macro_confidence_base": 0.50,
            "macro_confidence_weight_factor": 0.35,
            "macro_confidence_cap": 0.85,
        }
        # S-5: horizon per jenis jalur. Bawaan di sini mencerminkan isi YAML
        # supaya perilaku tidak berubah bila file tidak ada.
        self.horizon_policy: dict[str, Any] = {
            "explicit": "short",
            "macro": "medium",
            "intraday_keywords": [],
        }
        if self.config_path.exists():
            with open(self.config_path, mode="r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            section = data.get("routing") if isinstance(data, dict) else None
            if isinstance(section, dict):
                horizon = section.pop("horizon", None)
                self.routing.update(section)
                if isinstance(horizon, dict):
                    self.horizon_policy.update(horizon)

    def resolve_horizon(self, text: str, basis: Basis) -> NewsHorizon:
        """Horizon berita untuk satu dampak (S-5 / FR-23).

        Sebelumnya `news_horizon` selalu jatuh ke nilai bawaan SHORT karena
        router tidak pernah mengisinya — FR-23 hanya "terisi" secara teknis.

        Aturan, semuanya dari `router_config.yaml`:
        - kata kunci intraday muncul  -> INTRADAY (reda di hari yang sama)
        - jalur eksplisit             -> `horizon.explicit` (bawaan short)
        - jalur makro                 -> `horizon.macro` (bawaan medium)
        """
        lower = text.lower()
        for kw in self.horizon_policy.get("intraday_keywords", []) or []:
            if str(kw).lower() in lower:
                return NewsHorizon.INTRADAY

        key = "explicit" if basis is Basis.EXPLICIT else "macro"
        raw = str(self.horizon_policy.get(key, "short")).lower()
        try:
            return NewsHorizon(raw)
        except ValueError:
            # Konfigurasi salah tidak boleh menjatuhkan pipeline; pakai short
            # dan biarkan nilai mentahnya terlihat di log pemanggil.
            return NewsHorizon.SHORT

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
        self,
        article: Article,
        sentiment_score: float,
        model_version: str = "fusion-v1",
        model_router: Optional["ModelRouter"] = None,
    ) -> list[TargetImpact]:
        """
        Routes an article to target impacts via explicit mentions and macro themes.
        Strict rule: caps confidence by basis and builds evidence for explicit tags.

        Bila `model_router` diberikan, pilihan model spesialis dicatat di
        `routed_from`/`route_score` supaya keputusan routing dapat diaudit.
        """
        impacts: list[TargetImpact] = []
        full_text = f"{article.title} {article.body or ''}".strip()

        routed_from: Optional[str] = None
        route_score: Optional[float] = None
        if model_router is not None:
            models, reason, score = model_router.route(full_text, article.source or "")
            routed_from = f"{reason}:{'+'.join(models)}"
            route_score = score

        # 1. Explicit matches
        explicit_matches = self.find_explicit_mentions(full_text)
        tagged_assets = set()

        for asset_id, matched_alias, start, end in explicit_matches:
            tagged_assets.add(asset_id)
            # Direction follows sentiment score for explicit mentions
            threshold = self.routing["direction_threshold"]
            if sentiment_score > threshold:
                direction = Direction.BULLISH
            elif sentiment_score < -threshold:
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
                    confidence=self.routing["explicit_confidence"],
                    basis=Basis.EXPLICIT,
                    themes=[],
                    evidence=evidence,
                    flags=[],
                    news_horizon=self.resolve_horizon(full_text, Basis.EXPLICIT),
                    model_version=model_version,
                    routed_from=routed_from,
                    route_score=route_score,
                )
            )

        # 2. Macro themes mapping via impact_graph
        themes = self.detect_themes(full_text)
        for theme in themes:
            theme_targets = self.impact_graph.get(theme, [])
            for entry in theme_targets:
                macro_asset = entry.get("target")
                if not macro_asset or macro_asset not in LOCKED_UNIVERSE:
                    continue
                if macro_asset in tagged_assets:
                    continue  # Explicit priority

                sign = entry.get("sign", 1)
                weight = entry.get("weight", 0.5)
                projected_score = sentiment_score * sign * weight

                threshold = self.routing["direction_threshold"]
                if projected_score > threshold:
                    direction = Direction.BULLISH
                elif projected_score < -threshold:
                    direction = Direction.BEARISH
                else:
                    direction = Direction.NEUTRAL

                impacts.append(
                    TargetImpact(
                        article_id=article.article_id,
                        asset_id=macro_asset,
                        direction=direction,
                        score=max(-1.0, min(1.0, projected_score)),
                        confidence=min(
                            self.routing["macro_confidence_cap"],
                            self.routing["macro_confidence_base"]
                            + weight * self.routing["macro_confidence_weight_factor"],
                        ),
                        basis=Basis.MACRO_FACTOR,
                        themes=[theme],
                        causal_path=[theme, f"{macro_asset}_{direction.value}"],
                        evidence=[],
                        flags=[],
                        news_horizon=self.resolve_horizon(full_text, Basis.MACRO_FACTOR),
                        model_version=model_version,
                        routed_from=routed_from,
                        route_score=route_score,
                    )
                )

        return impacts
