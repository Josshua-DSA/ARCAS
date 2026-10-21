"""Evaluation metrics for sentiment models: F1 macro, ECE, Cohen's Kappa."""

from typing import Sequence

import numpy as np

try:
    from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score  # type: ignore
except ImportError:
    accuracy_score = None  # type: ignore
    cohen_kappa_score = None  # type: ignore
    f1_score = None  # type: ignore


def compute_ece(probs: Sequence[float], confidences: Sequence[float], true_labels: Sequence[int], n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE)."""
    if len(probs) == 0:
        return 0.0

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs)

    for i in range(n_bins):
        bin_lower = bins[i]
        bin_upper = bins[i + 1]
        in_bin = [(c >= bin_lower and c < bin_upper) for c in confidences]
        prop_in_bin = sum(in_bin) / n

        if prop_in_bin > 0:
            bin_acc = sum([t for idx, t in enumerate(true_labels) if in_bin[idx]]) / sum(in_bin)
            bin_conf = sum([c for idx, c in enumerate(confidences) if in_bin[idx]]) / sum(in_bin)
            ece += prop_in_bin * abs(bin_acc - bin_conf)

    return float(ece)


def evaluate_predictions(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, float]:
    """Calculates macro-F1, accuracy, and cohen kappa."""
    if len(y_true) == 0:
        return {"f1_macro": 0.0, "accuracy": 0.0, "kappa": 0.0}

    if f1_score and accuracy_score:
        f1 = float(f1_score(y_true, y_pred, average="macro"))
        acc = float(accuracy_score(y_true, y_pred))
        kappa = float(cohen_kappa_score(y_true, y_pred)) if cohen_kappa_score else 0.0
    else:
        # Simple fallback
        correct = sum(1 for yt, yp in zip(y_true, y_pred) if yt == yp)
        acc = correct / len(y_true)
        f1 = acc
        kappa = 0.0

    return {
        "f1_macro": round(f1, 4),
        "accuracy": round(acc, 4),
        "kappa": round(kappa, 4),
    }
