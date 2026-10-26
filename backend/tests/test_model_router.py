"""Tests for the two-stage cascade model router."""

import random
from pathlib import Path

import pytest

from backend.src.tagging.model_router import ModelRouter

WEIGHTS = Path("model/common/router_centroids.json")
requires_weights = pytest.mark.skipif(
    not WEIGHTS.exists(), reason="jalankan scripts/build_router_centroids.py dulu"
)


@pytest.fixture(scope="module")
def router() -> ModelRouter:
    return ModelRouter()


def test_source_hint_wins(router: ModelRouter) -> None:
    assert router.route("Gold rally continues", "kitco_rss") == (["finbert_emas"], "source", 1.0)
    assert router.route("Statement", "https://www.federalreserve.gov/feed") == (
        ["fomc_roberta"],
        "source",
        1.0,
    )


def test_keyword_plural(router: ModelRouter) -> None:
    models, reason, _ = router.route("Fed officials signal patience on rate cuts")
    assert models == ["fomc_roberta"] and reason == "keyword"


def test_dual_route_when_both_domains_present(router: ModelRouter) -> None:
    models, reason, _ = router.route("Gold hits record as Fed pauses")
    assert set(models) == {"finbert_emas", "fomc_roberta"} and reason == "keyword"


def test_indonesian_keywords(router: ModelRouter) -> None:
    assert router.route("Berita emas: harga logam mulia naik")[0] == ["finbert_emas"]


@requires_weights
def test_stage_two_catches_implicit_text(router: ModelRouter) -> None:
    models, reason, score = router.route("Committee judged that policy restraint may need to remain")
    assert models == ["fomc_roberta"] and reason == "log_odds" and score < 0


@requires_weights
def test_out_of_domain_falls_back(router: ModelRouter) -> None:
    """Teks di luar domain tidak boleh dirutekan karena satu kata kebetulan."""
    for text in ("Local weather forecast for Jakarta", "The company reported quarterly earnings"):
        assert router.route(text)[0] == ["baseline_tfidf"]


@requires_weights
def test_benchmark_accuracy(router: ModelRouter) -> None:
    """Uji cepat pada sampel dataset: akurasi rute harus tetap tinggi."""
    import pandas as pd

    gold = pd.read_parquet("dataset/gold_sinha/data/train-00000-of-00001.parquet")["News"].dropna()
    fomc = pd.read_excel("dataset/fomc/train/lab-manual-split-combine-train-5768.xlsx")[
        "sentence"
    ].dropna()
    random.seed(0)
    gold_hit = sum(
        1 for t in random.sample(list(gold), 200) if router.route(t)[0] == ["finbert_emas"]
    ) / 200
    fomc_hit = sum(
        1 for t in random.sample(list(fomc), 200) if router.route(t)[0] == ["fomc_roberta"]
    ) / 200
    assert gold_hit >= 0.90, f"akurasi gold turun: {gold_hit:.2%}"
    assert fomc_hit >= 0.90, f"akurasi fomc turun: {fomc_hit:.2%}"
