"""Deterministic Allocation Tilt engine satisfying strict 100% sum constraint."""

import math
from pathlib import Path

import yaml

from backend.src.schema import (
    AllocationLine,
    AllocationSuggestion,
    AllocClass,
    ClassScore,
)


class AllocationEngine:
    """Computes relative portfolio tilt adjustments from asset scores."""

    def __init__(
        self,
        profiles_path: Path | str = Path("data/alloc_profiles.yaml"),
        map_path: Path | str = Path("data/alloc_map.yaml"),
    ):
        self.profiles_path = Path(profiles_path)
        self.map_path = Path(map_path)
        self.profiles: dict = {}
        self.params: dict = {"lambda_tilt": 0.15, "delta_max_pp": 5.0, "conf_min": 0.40}
        self.mappings: dict = {}
        self._load_configs()

    def _load_configs(self) -> None:
        if self.profiles_path.exists():
            with open(self.profiles_path, mode="r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.profiles = data.get("profiles", {})
                self.params.update(data.get("params", {}))

        if self.map_path.exists():
            with open(self.map_path, mode="r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.mappings = data.get("mappings", {})

    def compute_class_scores(
        self, target_scores: dict[str, tuple[float, float]]  # asset_id -> (score, conf)
    ) -> dict[AllocClass, ClassScore]:
        """
        Derives scores for 6 allocation classes using alloc_map.yaml.
        Score tuple: (score, confidence)
        """
        class_scores: dict[AllocClass, ClassScore] = {}

        # Direct targets: GOLD (XAU), STOCK (SPX). The BTC class was
        # removed from AllocClass on main; classes below conf_min stay
        # pinned at baseline so the 100% balance holds regardless.
        direct_map = {
            AllocClass.GOLD: "XAU",
            AllocClass.STOCK: "SPX",
        }
        for alloc_cls, tgt in direct_map.items():
            sc, conf = target_scores.get(tgt, (0.0, 0.0))
            class_scores[alloc_cls] = ClassScore(
                alloc_class=alloc_cls, score=sc, confidence=conf, sources=[tgt]
            )

        # ETF: SPX only in the core3 universe (was SPX 60% + IHSG 40%)
        spx_s, spx_c = target_scores.get("SPX", (0.0, 0.0))
        class_scores[AllocClass.ETF] = ClassScore(
            alloc_class=AllocClass.ETF, score=spx_s, confidence=spx_c, sources=["SPX"]
        )

        # BOND: Macro derived from themes or proxy
        # Fallback to zero if not provided
        class_scores[AllocClass.BOND] = ClassScore(
            alloc_class=AllocClass.BOND, score=0.0, confidence=0.5, sources=["macro_theme"]
        )

        # MUTUAL_FUND: Blend of BOND (60%) and STOCK (40%)
        mf_score = 0.6 * class_scores[AllocClass.BOND].score + 0.4 * class_scores[AllocClass.STOCK].score
        mf_conf = 0.6 * class_scores[AllocClass.BOND].confidence + 0.4 * class_scores[AllocClass.STOCK].confidence
        class_scores[AllocClass.MUTUAL_FUND] = ClassScore(
            alloc_class=AllocClass.MUTUAL_FUND, score=mf_score, confidence=mf_conf, sources=["bond", "stock"]
        )

        return class_scores

    def tilt_portfolio(
        self,
        article_id: str,
        profile_id: str,
        class_scores: dict[AllocClass, ClassScore],
    ) -> AllocationSuggestion:
        """
        Calculates constrained allocation tilt for a specific profile.
        Strictly enforces: sum(new_pct) == 100.0% and min <= new_pct <= max.
        """
        profile = self.profiles.get(profile_id)
        if not profile:
            raise ValueError(f"Unknown profile: {profile_id}")

        classes_cfg = profile.get("classes", {})
        lambda_val = self.params.get("lambda_tilt", 0.15)
        delta_max = self.params.get("delta_max_pp", 5.0)
        conf_min = self.params.get("conf_min", 0.40)

        # Step 1: Compute raw unnormalized weights
        raw_weights: dict[AllocClass, float] = {}
        for cls_enum in AllocClass:
            if cls_enum.value not in classes_cfg:
                continue
            cfg = classes_cfg[cls_enum.value]
            base_pct = float(cfg["base_pct"])
            cs = class_scores.get(cls_enum, ClassScore(alloc_class=cls_enum, score=0.0, confidence=0.0))

            if cs.confidence < conf_min:
                raw_weights[cls_enum] = base_pct
            else:
                raw_w = base_pct * math.exp(lambda_val * cs.score * cs.confidence)
                raw_weights[cls_enum] = raw_w

        # Step 2: Normalize to 100%
        sum_raw = sum(raw_weights.values()) or 100.0
        norm_weights = {k: (w / sum_raw) * 100.0 for k, w in raw_weights.items()}

        # Step 3: Apply min/max clip and delta_max clip
        lines: list[AllocationLine] = []
        tentative: dict[AllocClass, float] = {}
        for cls_enum, w in norm_weights.items():
            cfg = classes_cfg[cls_enum.value]
            base_pct = float(cfg["base_pct"])
            min_pct = float(cfg["min_pct"])
            max_pct = float(cfg["max_pct"])

            # Delta clip
            delta = w - base_pct
            clipped_delta = max(-delta_max, min(delta_max, delta))
            target_w = base_pct + clipped_delta

            # Boundary clip
            bounded_w = max(min_pct, min(max_pct, target_w))
            tentative[cls_enum] = bounded_w

        # Pin low-confidence classes back to baseline: normalization in
        # Step 2 would otherwise drag them along with the tilted classes.
        # The flexible classes absorb the difference below.
        for cls_enum in list(tentative.keys()):
            cs = class_scores.get(
                cls_enum, ClassScore(alloc_class=cls_enum, score=0.0, confidence=0.0)
            )
            if cs.confidence < conf_min:
                tentative[cls_enum] = float(classes_cfg[cls_enum.value]["base_pct"])

        # Step 4: Water-filling residual adjustment to guarantee exact 100.0% sum.
        # Low-confidence classes stay pinned at baseline; the residual is
        # spread over flexible classes only.
        total_tentative = sum(tentative.values())
        diff = 100.0 - total_tentative

        sorted_classes = sorted(tentative.keys(), key=lambda k: tentative[k], reverse=True)
        frozen = {
            cls_enum
            for cls_enum in sorted_classes
            if class_scores.get(
                cls_enum, ClassScore(alloc_class=cls_enum, score=0.0, confidence=0.0)
            ).confidence
            < conf_min
        }
        flexible = [c for c in sorted_classes if c not in frozen] or list(sorted_classes)
        adj_per_class = diff / len(flexible)
        final_weights = {}
        for cls_enum in sorted_classes:
            add = adj_per_class if cls_enum in flexible else 0.0
            final_weights[cls_enum] = round(tentative[cls_enum] + add, 2)

        # Fix rounding residual on largest flexible class
        residual = round(100.0 - sum(final_weights.values()), 2)
        if abs(residual) > 0.001:
            first_cls = flexible[0]
            final_weights[first_cls] = round(final_weights[first_cls] + residual, 2)

        # Build output lines
        for cls_enum, new_w in final_weights.items():
            cfg = classes_cfg[cls_enum.value]
            base_pct = float(cfg["base_pct"])
            cs = class_scores.get(cls_enum, ClassScore(alloc_class=cls_enum, score=0.0, confidence=0.0))
            delta_pp = round(new_w - base_pct, 2)
            no_change = abs(delta_pp) < 0.01

            rationale = (
                f"Sinyal {cs.score:+.2f} (conf {cs.confidence:.2f}) menghasilkan pergeseran {delta_pp:+.2f} pp."
                if not no_change
                else "Tidak ada perubahan alokasi signifikan."
            )

            lines.append(
                AllocationLine(
                    alloc_class=cls_enum,
                    baseline_pct=base_pct,
                    new_pct=new_w,
                    delta_pp=delta_pp,
                    confidence=cs.confidence,
                    rationale=rationale,
                    no_change=no_change,
                )
            )

        return AllocationSuggestion(
            article_id=article_id,
            profile_id=profile_id,
            lines=lines,
            params_version="2026-10-12-core3",
            disclaimer="Simulasi analitis. Bukan nasihat investasi.",
        )
