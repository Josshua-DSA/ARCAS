"""Unit tests for FOMC track data loader and methodology contracts."""

import pytest

from model.fomc.src.data_loader import (
    DEFAULT_FOMC_TEST_PATH,
    DEFAULT_FOMC_TRAIN_PATH,
    LABEL_TO_STANCE,
    STANCE_TO_TONE,
    get_fomc_texts_and_labels,
    load_fomc_test_holdout,
    load_fomc_train_raw,
    load_fomc_train_val_split,
)


@pytest.mark.skipif(not DEFAULT_FOMC_TRAIN_PATH.exists(), reason="FOMC train dataset missing")
def test_fomc_train_loading_and_counts():
    """Validates that train set loads exactly 1.939 valid rows with required columns."""
    df_train = load_fomc_train_raw()
    assert len(df_train) == 1939
    assert {"sentence", "label", "stance", "tone_RATE_UST", "tone_SPX"}.issubset(df_train.columns)

    # Valid label values: 0 (Dovish), 1 (Hawkish), 2 (Neutral)
    labels = set(df_train["label"].unique())
    assert labels == {0, 1, 2}

    # Verify label counts match official dataset
    counts = df_train["label"].value_counts().to_dict()
    assert counts[2] == 955  # Neutral
    assert counts[0] == 512  # Dovish
    assert counts[1] == 472  # Hawkish


@pytest.mark.skipif(not DEFAULT_FOMC_TRAIN_PATH.exists(), reason="FOMC train dataset missing")
def test_fomc_stratified_split():
    """Validates stratified 90:10 split (1.745 train vs 194 validation)."""
    df_train, df_val = load_fomc_train_val_split(val_ratio=0.10, seed=5768)

    assert len(df_train) == 1745
    assert len(df_val) == 194
    assert len(df_train) + len(df_val) == 1939

    # Verify class proportions are preserved in validation split within 1%
    total_val = len(df_val)
    val_counts = df_val["label"].value_counts().to_dict()
    p_neutral = val_counts[2] / total_val
    p_dovish = val_counts[0] / total_val
    p_hawkish = val_counts[1] / total_val

    # Expected proportions: Neutral ~49.2%, Dovish ~26.4%, Hawkish ~24.3%
    assert 0.45 <= p_neutral <= 0.53
    assert 0.23 <= p_dovish <= 0.30
    assert 0.21 <= p_hawkish <= 0.28


@pytest.mark.skipif(not DEFAULT_FOMC_TEST_PATH.exists(), reason="FOMC test dataset missing")
def test_fomc_test_holdout_isolation():
    """Validates that official unseen test set has exactly 495 rows."""
    df_test = load_fomc_test_holdout()
    assert len(df_test) == 495

    test_counts = df_test["label"].value_counts().to_dict()
    assert test_counts[2] == 244  # Neutral
    assert test_counts[0] == 129  # Dovish
    assert test_counts[1] == 122  # Hawkish


def test_fomc_dual_target_inverse_mapping():
    """Validates monetary stance transmission invariant to RATE_UST and SPX."""
    # Hawkish: Yield up (+), Stocks down (-)
    assert STANCE_TO_TONE[("hawkish", "RATE_UST")] == "positive"
    assert STANCE_TO_TONE[("hawkish", "SPX")] == "negative"

    # Dovish: Yield down (-), Stocks up (+)
    assert STANCE_TO_TONE[("dovish", "RATE_UST")] == "negative"
    assert STANCE_TO_TONE[("dovish", "SPX")] == "positive"

    # Neutral: Neutral for both
    assert STANCE_TO_TONE[("neutral", "RATE_UST")] == "neutral"
    assert STANCE_TO_TONE[("neutral", "SPX")] == "neutral"


@pytest.mark.skipif(not DEFAULT_FOMC_TRAIN_PATH.exists(), reason="FOMC train dataset missing")
def test_get_fomc_texts_and_labels():
    """Validates extracting clean lists of texts and integer labels."""
    df_train, df_val = load_fomc_train_val_split(val_ratio=0.10, seed=5768)
    texts, labels = get_fomc_texts_and_labels(df_val)

    assert len(texts) == 194
    assert len(labels) == 194
    assert isinstance(texts[0], str)
    assert isinstance(labels[0], int)


def test_softmax_temperature_properties():
    """Validates invariant that probabilities always sum to 1.0 and soften with higher T."""
    import numpy as np
    from model.fomc.src.calibrator import softmax

    logits = np.array([[2.0, 1.0, 0.0], [0.5, 3.0, 0.2]])

    # Row sums must equal 1.0
    for T in [0.5, 1.0, 2.0, 5.0]:
        probs = softmax(logits, temperature=T)
        assert np.allclose(np.sum(probs, axis=-1), 1.0, atol=1e-5)

    # As T increases, highest confidence should decrease (entropy increases)
    p_sharp = softmax(logits, temperature=0.5)
    p_soft = softmax(logits, temperature=2.0)
    assert p_sharp[0, 0] > p_soft[0, 0]


def test_multiclass_ece_calculation():
    """Validates multi-class Expected Calibration Error (ECE) metric."""
    import numpy as np
    from model.fomc.src.calibrator import compute_multiclass_ece

    # Case 1: Perfectly calibrated probabilities (confidence matches accuracy)
    probs_perfect = np.array([[0.9, 0.05, 0.05], [0.1, 0.8, 0.1]])
    labels_perfect = [0, 1]
    ece_good = compute_multiclass_ece(probs_perfect, labels_perfect)
    assert ece_good <= 0.20

    # Case 2: Highly overconfident wrong predictions
    probs_bad = np.array([[0.99, 0.01, 0.0], [0.99, 0.0, 0.01]])
    labels_bad = [1, 2]  # Actual classes are 1 and 2, but model is 99% confident in 0
    ece_bad = compute_multiclass_ece(probs_bad, labels_bad)
    assert ece_bad > 0.80


def test_temperature_scaler_fit_and_persistence(tmp_path):
    """Validates TemperatureScaler fitting, scaling, and JSON persistence."""
    import numpy as np
    from model.fomc.src.calibrator import TemperatureScaler

    # Generate slightly overconfident synthetic logits for 3 classes
    np.random.seed(5768)
    n = 100
    labels = np.random.choice([0, 1, 2], size=n)
    # Give highest logit to correct class on 70% of samples, but with large magnitude (overconfident)
    logits = np.random.randn(n, 3) * 0.5
    for i in range(n):
        if np.random.rand() < 0.70:
            logits[i, labels[i]] += 4.0  # high confidence correct
        else:
            wrong_class = (labels[i] + 1) % 3
            logits[i, wrong_class] += 4.0  # high confidence wrong

    scaler = TemperatureScaler()
    opt_t = scaler.fit(logits, labels)

    assert opt_t > 0.0
    assert scaler.ece_pre is not None
    assert scaler.ece_post is not None
    assert scaler.ece_post <= scaler.ece_pre  # Temperature scaling should reduce or keep ECE

    # Test predict_proba invariant
    cal_probs = scaler.predict_proba(logits)
    assert cal_probs.shape == (n, 3)
    assert np.allclose(np.sum(cal_probs, axis=-1), 1.0, atol=1e-5)

    # Test save and load
    save_file = tmp_path / "temperature.json"
    scaler.save(save_file)
    assert save_file.exists()

    loaded_scaler = TemperatureScaler.load(save_file)
    assert np.isclose(loaded_scaler.temperature, opt_t, atol=1e-5)
    assert np.isclose(loaded_scaler.ece_pre, scaler.ece_pre, atol=1e-5)


@pytest.mark.skipif(not DEFAULT_FOMC_TRAIN_PATH.exists(), reason="FOMC train dataset missing")
def test_train_fomc_baseline(tmp_path):
    """Validates training and serializing the FOMC baseline TF-IDF + LR model."""
    import joblib
    from model.fomc.src.model import train_fomc_baseline

    df_train, df_val = load_fomc_train_val_split(val_ratio=0.10, seed=5768)
    save_path = tmp_path / "baseline_fomc.joblib"

    # Train on small subset for fast unit testing
    df_mini = df_train.iloc[:100]
    vec, clf, p = train_fomc_baseline(df_mini, out_path=save_path)

    assert p.exists()
    assert save_path.exists()

    # Load and test inference
    loaded = joblib.load(save_path)
    X_val = loaded["vectorizer"].transform(["Federal Reserve signals aggressive rate hike."])
    pred = loaded["classifier"].predict(X_val)
    assert pred[0] in [0, 1, 2]


def test_fomc_roberta_protocol_properties():
    """Validates BaseSentimentModel protocol compliance without downloading heavy checkpoint."""
    from model.fomc.src.model import FOMCRoBERTaSentiment

    # Instantiate in lazy mode
    model = FOMCRoBERTaSentiment(lazy_load=True)
    assert model.model_name == "fomc_roberta"
    assert model.model_version == "fomc-roberta-v1.0"
    assert model.calibrator is not None


def test_compute_mcnemar_significance():
    """Validates McNemar 2x2 contingency table calculation and p-value."""
    from model.fomc.evaluation.evaluate_holdout import compute_mcnemar_test

    y_true = [0, 1, 2, 0, 1, 2] * 20  # 120 samples
    y_pred_base = list(y_true)
    y_pred_roberta = list(y_true)

    # Make baseline fail on 25 samples where roberta succeeds (n01 = 25, n10 = 0)
    for i in range(25):
        y_pred_base[i] = (y_true[i] + 1) % 3

    res = compute_mcnemar_test(y_true, y_pred_base, y_pred_roberta)
    assert res["contingency_table"]["roberta_correct_baseline_wrong_n01"] == 25
    assert res["contingency_table"]["baseline_correct_roberta_wrong_n10"] == 0
    assert res["significant_p_05"] is True
    assert res["component_adopted"] is True
    assert res["p_value"] < 0.001


def test_compute_bootstrap_ci():
    """Validates bootstrap 95% confidence interval for difference in Macro F1."""
    from model.fomc.evaluation.evaluate_holdout import compute_bootstrap_ci

    y_true = [0, 1, 2] * 30
    y_pred_base = [(y + 1) % 3 if i < 30 else y for i, y in enumerate(y_true)]
    y_pred_roberta = list(y_true)  # perfect predictions

    res = compute_bootstrap_ci(y_true, y_pred_base, y_pred_roberta, n_bootstraps=200, seed=5768)
    assert res["mean_delta_macro_f1"] > 0.0
    assert res["ci_strictly_positive"] is True
    assert res["ci_95_lower"] < res["mean_delta_macro_f1"] < res["ci_95_upper"]



