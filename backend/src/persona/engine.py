"""Deterministic Persona POV engine computing BUY/HOLD/SELL stances."""

from pathlib import Path
import yaml

from backend.src.schema import NewsHorizon, PersonaView, Stance


class PersonaEngine:
    """Evaluates 5 investor personas stances for a given impact."""

    def __init__(self, personas_path: Path | str = Path("data/personas.yaml")):
        self.personas_path = Path(personas_path)
        self.personas: dict = {}
        self._load_config()

    def _load_config(self) -> None:
        if self.personas_path.exists():
            with open(self.personas_path, mode="r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.personas = data.get("personas", {})

    @staticmethod
    def horizon_match(news_h: NewsHorizon, persona_h: str) -> float:
        """Calculates decay/alignment between news horizon and persona horizon."""
        weights = {
            "intraday": {"short": 0.8, "medium": 0.3, "long": 0.1},
            "short": {"short": 1.0, "medium": 0.6, "long": 0.2},
            "medium": {"short": 0.5, "medium": 1.0, "long": 0.7},
            "long": {"short": 0.1, "medium": 0.5, "long": 1.0},
        }
        return weights.get(news_h.value, {}).get(persona_h, 0.5)

    def evaluate_persona(
        self,
        article_id: str,
        persona_id: str,
        target: str,
        score: float,
        confidence: float,
        news_horizon: NewsHorizon = NewsHorizon.SHORT,
    ) -> PersonaView:
        """
        Calculates stance for a specific persona based on parameters.
        Deterministic rule: buy/sell thresholding + loss aversion multiplier.
        """
        p_cfg = self.personas.get(persona_id, {})
        persona_horizon = p_cfg.get("horizon", "medium")
        loss_aversion = float(p_cfg.get("loss_aversion", 0.20))
        theta = float(p_cfg.get("theta", 0.25))
        conf_min = float(p_cfg.get("conf_min", 0.50))

        match = self.horizon_match(news_horizon, persona_horizon)
        raw = score * confidence * match

        # Apply asymmetric loss aversion penalty
        if raw < 0:
            raw = raw * (1.0 + loss_aversion)

        # Decide stance
        if confidence >= conf_min and raw >= theta:
            stance = Stance.BUY
            rationale_tpl = f"Sinyal bullish terkonfirmasi melampaui ambang ({raw:+.2f} >= {theta:.2f})."
        elif confidence >= conf_min and raw <= -theta:
            stance = Stance.SELL
            rationale_tpl = f"Sinyal risiko negatif terpicu dengan penalti mitigasi ({raw:+.2f} <= {-theta:.2f})."
        else:
            stance = Stance.HOLD
            if confidence < conf_min:
                rationale_tpl = f"Tingkat keyakinan ({confidence:.2f}) di bawah batas minimum ({conf_min:.2f})."
            else:
                rationale_tpl = f"Intensitas sinyal ({abs(raw):.2f}) berada di dalam rentang netral."

        strength = min(1.0, abs(raw) / (2.0 * theta)) if theta > 0 else 0.0

        return PersonaView(
            article_id=article_id,
            persona_id=persona_id,
            target=target,
            stance=stance,
            strength=round(strength, 4),
            news_horizon=news_horizon,
            raw_value=round(raw, 4),
            confidence=round(confidence, 4),
            rationale=rationale_tpl,
            params_version="2026-10-09",
            disclaimer="Simulasi sudut pandang. Bukan nasihat investasi.",
        )

    def evaluate_all(
        self,
        article_id: str,
        target: str,
        score: float,
        confidence: float,
        news_horizon: NewsHorizon = NewsHorizon.SHORT,
    ) -> list[PersonaView]:
        """Evaluates all 5 personas."""
        return [
            self.evaluate_persona(
                article_id=article_id,
                persona_id=p_id,
                target=target,
                score=score,
                confidence=confidence,
                news_horizon=news_horizon,
            )
            for p_id in ["retail", "day_trader", "fund_manager", "pension", "risk_manager"]
        ]
