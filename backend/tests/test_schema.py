"""Unit tests for SCHEMA v0.5.0 data contracts and invariants."""

from datetime import date, datetime

import pytest
from pydantic import ValidationError

from backend.src.schema import (
    AllocationLine,
    AllocationSuggestion,
    AllocClass,
    Basis,
    DailySentiment,
    Direction,
    EvidenceSpan,
    ModelProbs,
    TargetImpact,
)


def test_model_probs_sum_to_one():
    """Probabilities must sum to 1.0 within tolerance."""
    # Valid
    p = ModelProbs(model="indobert", p_pos=0.6, p_neu=0.3, p_neg=0.1, model_version="v1")
    assert p.p_pos == 0.6

    # Invalid sum
    with pytest.raises(ValidationError):
        ModelProbs(model="indobert", p_pos=0.8, p_neu=0.3, p_neg=0.1, model_version="v1")


def test_target_impact_invariants():
    """TargetImpact direction and basis confidence caps must hold."""
    evidence = [EvidenceSpan(quote="Pertumbuhan ekonomi melampaui target", start=0, end=35)]

    # Explicit basis with valid confidence
    impact = TargetImpact(
        article_id="art123",
        asset_id="SPX",
        direction=Direction.BULLISH,
        score=0.45,
        confidence=0.90,
        basis=Basis.EXPLICIT,
        evidence=evidence,
        model_version="indobert-v1",
        universe_version="2026-10-12-core3",
        schema_version="v0.5.0",
        created_at=datetime.utcnow(),
    )
    assert impact.score == 0.45

    # Sector inferred cannot exceed 0.60
    with pytest.raises(ValidationError):
        TargetImpact(
            article_id="art123",
            asset_id="SPX",
            direction=Direction.BULLISH,
            score=0.45,
            confidence=0.85,  # Exceeds cap 0.60!
            basis=Basis.SECTOR_INFERRED,
            evidence=evidence,
            model_version="indobert-v1",
            universe_version="2026-10-12-core3",
            schema_version="v0.5.0",
            created_at=datetime.utcnow(),
        )


def test_daily_sentiment_empty_invariant():
    """When n_articles == 0, score_mean must be None (not 0.0) and has_news == False."""
    valid_empty = DailySentiment(
        asset_id="XAU",
        date=date(2026, 10, 9),
        score_mean=None,
        n_articles=0,
        n_sources=0,
        has_news=False,
    )
    assert valid_empty.score_mean is None

    # Invalid: n_articles == 0 but score_mean is given
    with pytest.raises(ValidationError):
        DailySentiment(
            asset_id="XAU",
            date=date(2026, 10, 9),
            score_mean=0.0,
            n_articles=0,
            n_sources=0,
            has_news=False,
        )


def test_allocation_suggestion_sum_100():
    """Allocation lines must sum strictly to 100.0%."""
    lines = [
        AllocationLine(alloc_class=AllocClass.BOND, baseline_pct=50.0, new_pct=50.0, delta_pp=0.0, confidence=0.7),
        AllocationLine(alloc_class=AllocClass.STOCK, baseline_pct=30.0, new_pct=30.0, delta_pp=0.0, confidence=0.7),
        AllocationLine(alloc_class=AllocClass.GOLD, baseline_pct=20.0, new_pct=20.0, delta_pp=0.0, confidence=0.7),
    ]

    suggestion = AllocationSuggestion(
        article_id="art1",
        profile_id="moderate",
        lines=lines,
        params_version="2026-10-12-core3",
        disclaimer="Bukan nasihat investasi.",
    )
    assert len(suggestion.lines) == 3

    # Invalid sum (not 100%)
    bad_lines = [
        AllocationLine(alloc_class=AllocClass.BOND, baseline_pct=50.0, new_pct=45.0, delta_pp=-5.0, confidence=0.7),
        AllocationLine(alloc_class=AllocClass.STOCK, baseline_pct=30.0, new_pct=30.0, delta_pp=0.0, confidence=0.7),
    ]
    with pytest.raises(ValidationError):
        AllocationSuggestion(
            article_id="art1",
            profile_id="moderate",
            lines=bad_lines,
            params_version="2026-10-12-core3",
            disclaimer="Bukan nasihat investasi.",
        )
