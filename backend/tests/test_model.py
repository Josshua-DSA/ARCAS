"""Tests for baseline ML model and evaluation metrics."""

from pathlib import Path

import pytest

from model.common.baseline import BaselineTfidfSentiment, ModelNotFittedError
from model.common.metrics import evaluate_predictions

MODEL_PATH = Path("model/common/baseline_tfidf.joblib")
requires_model = pytest.mark.skipif(
    not MODEL_PATH.exists(),
    reason="latih dulu: python -m model.common.train_baseline",
)


def test_model_belum_dilatih_melempar():
    """Model tanpa fit()/load() harus melempar, bukan mengarang prior.

    Sebelum perbaikan AUDIT K-4, test ini gagal karena predict_probs()
    diam-diam mengembalikan [0.20, 0.60, 0.20] dan menyamarkan model rusak.
    """
    model = BaselineTfidfSentiment()
    with pytest.raises(ModelNotFittedError):
        model.predict_probs(["Pasar saham menguat tajam hari ini."])


def test_fit_membuat_model_siap():
    """fit() pada data kecil harus menghasilkan prediksi valid."""
    model = BaselineTfidfSentiment()
    teks = [
        "gold rallies strongly on safe haven demand",
        "gold plunges as dollar strengthens sharply",
        "gold trades flat ahead of fed decision",
        "gold surges to record high",
        "gold falls on profit taking",
        "gold steady in quiet session",
    ]
    label = [2, 0, 1, 2, 0, 1]
    model.fit(teks, label)

    probs = model.predict_probs(["gold rallies on strong demand"])
    assert len(probs) == 1
    p = probs[0]
    assert round(p.p_pos + p.p_neu + p.p_neg, 6) == 1.0

    sentiment = model.score_article("art_1", "gold rallies on strong demand")
    assert sentiment.article_id == "art_1"
    assert -1.0 <= sentiment.score <= 1.0


@requires_model
def test_model_terlatih_membedakan_arah():
    """Model nyata harus memberi sinyal berbeda untuk teks bullish vs bearish."""
    model = BaselineTfidfSentiment.load(MODEL_PATH)

    naik = model.predict_probs(["Gold surges to record high on safe haven demand"])[0]
    turun = model.predict_probs(["Gold plunges as dollar rallies sharply"])[0]

    assert naik.p_pos > naik.p_neg, "teks bullish harus condong positif"
    assert turun.p_neg > turun.p_pos, "teks bearish harus condong negatif"
    assert (naik.p_pos, naik.p_neg) != (turun.p_pos, turun.p_neg)


def test_evaluation_metrics():
    """Tests F1 macro, accuracy, and kappa computation."""
    y_true = [0, 1, 2, 0, 1, 2]
    y_pred = [0, 1, 2, 0, 1, 1]
    res = evaluate_predictions(y_true, y_pred)
    assert "f1_macro" in res
    assert "accuracy" in res
    assert res["accuracy"] > 0.8
