"""Adapter tests: putus `none` gold + mapping FOMC (DESIGN §3.4)."""

import pandas as pd

from backend.src.normalize.adapters import (
    fomc_stance,
    fomc_to_raw,
    fomc_tone,
    gold_to_raw,
    gold_tone,
)


def test_gold_tone_drop_none():
    assert gold_tone("positive") == "positive"
    assert gold_tone("negative") == "negative"
    assert gold_tone("neutral") == "neutral"
    assert gold_tone("none") is None
    assert gold_tone("NONE") is None


def test_fomc_mapping_nonobvious():
    # Paper/repo mapping: LABEL_2 Neutral, LABEL_1 Hawkish, LABEL_0 Dovish.
    assert fomc_stance(2) == "neutral"
    assert fomc_stance(1) == "hawkish"
    assert fomc_stance(0) == "dovish"
    # Satu stance, dua target polaritas berlawanan.
    assert fomc_tone("hawkish", "RATE_UST") == "positive"
    assert fomc_tone("hawkish", "SPX") == "negative"
    assert fomc_tone("dovish", "RATE_UST") == "negative"
    assert fomc_tone("dovish", "SPX") == "positive"
    assert fomc_tone("neutral", "RATE_UST") == "neutral"
    assert fomc_tone("neutral", "SPX") == "neutral"


def test_gold_adapter_drops_none_and_dedups():
    df = pd.DataFrame(
        [
            {
                "Dates": "25-12-2007",
                "URL": "https://example.com/a",
                "News": "gold prices recover on buying support",
                "Price Sentiment": "positive",
            },
            {
                "Dates": "06-03-2012",
                "URL": "https://example.com/b",
                "News": "gold prices trading mixed in india",
                "Price Sentiment": "none",
            },
            {
                "Dates": "25-12-2007",
                "URL": "https://example.com/a",
                "News": "gold prices recover on buying support",
                "Price Sentiment": "positive",
            },
        ]
    )
    out = gold_to_raw(df)
    assert len(out) == 1
    assert out.iloc[0]["tone"] == "positive"
    assert out.iloc[0]["asset_id"] == "XAU"


def test_fomc_adapter_dual_tone():
    df = pd.DataFrame(
        [
            {
                "sentence": "Our mandate, sorry, is price inflation.",
                "year": 2021,
                "label": 1,
                "orig_index": 178,
            },
            {
                "sentence": "The Committee's assessments will take into account a wide range of information.",
                "year": 2004,
                "label": 2,
                "orig_index": 812,
            },
        ]
    )
    out = fomc_to_raw(df)
    assert len(out) == 2
    hawk = out[out["stance"] == "hawkish"].iloc[0]
    assert hawk["tone_RATE_UST"] == "positive"
    assert hawk["tone_SPX"] == "negative"
