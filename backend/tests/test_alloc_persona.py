"""Tests for Allocation Tilt engine and Persona POV engine."""

from backend.src.alloc.engine import AllocationEngine
from backend.src.persona.engine import PersonaEngine
from backend.src.schema import NewsHorizon, Stance


def test_allocation_tilt_exact_100_percent():
    """Validates that allocation tilt outputs strictly sum to 100.0%."""
    engine = AllocationEngine()
    scores = {
        "XAU": (0.40, 0.85),
        "SPX": (0.35, 0.90),
        "RATE_UST": (0.10, 0.65),
    }
    class_scores = engine.compute_class_scores(scores)

    for profile in ["conservative", "moderate", "aggressive"]:
        suggestion = engine.tilt_portfolio("art_test_1", profile, class_scores)
        total_pct = sum(line.new_pct for line in suggestion.lines)
        assert abs(total_pct - 100.0) < 1e-3, f"Profile {profile} does not sum to 100%: {total_pct}"
        assert suggestion.disclaimer == "Simulasi analitis. Bukan nasihat investasi."


def test_persona_evaluator_stances():
    """Validates persona stance logic under positive and negative signals."""
    engine = PersonaEngine()

    # Strong bullish signal
    bull_views = engine.evaluate_all(
        article_id="art_bull",
        target="SPX",
        score=0.80,
        confidence=0.90,
        news_horizon=NewsHorizon.SHORT,
    )
    assert len(bull_views) == 5
    day_trader = next(v for v in bull_views if v.persona_id == "day_trader")
    assert day_trader.stance == Stance.BUY

    # Strong bearish signal with loss aversion
    bear_views = engine.evaluate_all(
        article_id="art_bear",
        target="SPX",
        score=-0.80,
        confidence=0.90,
        news_horizon=NewsHorizon.SHORT,
    )
    assert len(bear_views) == 5
    risk_mgr = next(v for v in bear_views if v.persona_id == "risk_manager")
    assert risk_mgr.stance == Stance.SELL
