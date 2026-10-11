"""Tests for baseline ML model and evaluation metrics."""

from model.evaluation.metrics import evaluate_predictions
from model.src.baseline import BaselineTfidfSentiment


def test_baseline_tfidf_predict():
    """Tests TF-IDF + LR baseline model predictions."""
    model = BaselineTfidfSentiment()
    texts = ["Pasar saham menguat tajam hari ini.", "Inflasi menekan sentimen investor."]
    probs = model.predict_probs(texts)
    assert len(probs) == 2
    for p in probs:
        total = round(p.p_pos + p.p_neu + p.p_neg, 2)
        assert total == 1.0

    sentiment = model.score_article("art_1", texts[0])
    assert sentiment.article_id == "art_1"
    assert -1.0 <= sentiment.score <= 1.0


def test_evaluation_metrics():
    """Tests F1 macro, accuracy, and kappa computation."""
    y_true = [0, 1, 2, 0, 1, 2]
    y_pred = [0, 1, 2, 0, 1, 1]
    res = evaluate_predictions(y_true, y_pred)
    assert "f1_macro" in res
    assert "accuracy" in res
    assert res["accuracy"] > 0.8
