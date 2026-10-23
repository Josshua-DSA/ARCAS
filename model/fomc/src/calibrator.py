"""Probability calibrator using Temperature Scaling (M6) for FOMC-RoBERTa.

Reference:
    Guo, C., Pleiss, G., Sun, Y., & Weinberger, K. Q. (2017).
    "On Calibration of Modern Neural Networks", ICML 2017.

Formula:
    p_i = exp(z_i / T) / sum_j(exp(z_j / T))
    where T > 0 is a scalar learned by minimizing Negative Log-Likelihood (NLL)
    on the held-out validation set (194 samples).

Acceptance Criterion:
    Expected Calibration Error (ECE) <= 0.10 post-calibration.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence

import numpy as np
from scipy.optimize import minimize_scalar

DEFAULT_TEMPERATURE_PATH = Path("model/fomc/weights/temperature.json")


def softmax(logits: np.ndarray, temperature: float = 1.0) -> np.ndarray:
    """Computes numerically stable softmax probabilities with temperature scaling."""
    if temperature <= 0:
        raise ValueError(f"Temperature must be strictly positive, got {temperature}")

    scaled = logits / temperature
    # Subtract max per row for numerical stability
    shifted = scaled - np.max(scaled, axis=-1, keepdims=True)
    exp_vals = np.exp(shifted)
    probs = exp_vals / np.sum(exp_vals, axis=-1, keepdims=True)
    return probs


def compute_multiclass_ece(
    probs: np.ndarray,
    true_labels: Sequence[int],
    n_bins: int = 10,
) -> float:
    """Computes Expected Calibration Error (ECE) for multi-class predictions.

    Args:
        probs: Array of shape (N, C) containing predicted probabilities.
        true_labels: Sequence of length N containing true integer class labels.
        n_bins: Number of equal-width confidence bins (default: 10).

    Returns:
        float: Expected Calibration Error value between 0.0 and 1.0.
    """
    n = len(true_labels)
    if n == 0 or len(probs) == 0:
        return 0.0

    preds = np.argmax(probs, axis=-1)
    confs = np.max(probs, axis=-1)
    accuracies = (preds == np.array(true_labels)).astype(float)

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        bin_lower = bins[i]
        bin_upper = bins[i + 1]

        # Samples belonging to current bin
        if i == n_bins - 1:
            in_bin = (confs >= bin_lower) & (confs <= bin_upper)
        else:
            in_bin = (confs >= bin_lower) & (confs < bin_upper)

        prop_in_bin = np.sum(in_bin) / n

        if prop_in_bin > 0:
            bin_acc = np.mean(accuracies[in_bin])
            bin_conf = np.mean(confs[in_bin])
            ece += prop_in_bin * abs(bin_acc - bin_conf)

    return float(ece)


class TemperatureScaler:
    """Scales logits by optimal temperature parameter T to calibrate prediction probabilities."""

    def __init__(self, temperature: float = 1.0):
        self.temperature: float = float(temperature)
        self.ece_pre: Optional[float] = None
        self.ece_post: Optional[float] = None
        self.fitted_at: Optional[datetime] = None
        self.n_samples: Optional[int] = None

    def fit(
        self,
        logits: np.ndarray,
        labels: Sequence[int],
        bounds: tuple[float, float] = (0.1, 10.0),
    ) -> float:
        """Finds optimal temperature T by minimizing Negative Log-Likelihood (NLL) on validation logits.

        Args:
            logits: Matrix of raw unnormalized logits of shape (N, 3).
            labels: True class labels of length N (values in {0, 1, 2}).
            bounds: Search bounds for scalar temperature T.

        Returns:
            float: Optimal temperature T.
        """
        logits_arr = np.asarray(logits, dtype=float)
        labels_arr = np.asarray(labels, dtype=int)
        n = len(labels_arr)

        if n == 0 or logits_arr.shape[0] != n:
            raise ValueError(f"Logits shape {logits_arr.shape} does not match label count {n}")

        # Compute initial ECE with T = 1.0 (uncalibrated)
        initial_probs = softmax(logits_arr, temperature=1.0)
        self.ece_pre = compute_multiclass_ece(initial_probs, labels_arr)

        def nll_objective(t: float) -> float:
            scaled_probs = softmax(logits_arr, temperature=t)
            # Clip probabilities to prevent log(0)
            eps = 1e-12
            clipped_probs = np.clip(scaled_probs, eps, 1.0 - eps)
            # Negative log-likelihood of true classes
            true_class_probs = clipped_probs[np.arange(n), labels_arr]
            return float(-np.mean(np.log(true_class_probs)))

        res = minimize_scalar(nll_objective, bounds=bounds, method="bounded")
        self.temperature = float(res.x)

        # Compute post-calibration ECE
        calibrated_probs = softmax(logits_arr, temperature=self.temperature)
        self.ece_post = compute_multiclass_ece(calibrated_probs, labels_arr)
        self.fitted_at = datetime.now(timezone.utc)
        self.n_samples = n

        return self.temperature

    def scale_logits(self, logits: np.ndarray) -> np.ndarray:
        """Scales raw logits by learned temperature: z / T."""
        return np.asarray(logits, dtype=float) / self.temperature

    def predict_proba(self, logits: np.ndarray) -> np.ndarray:
        """Converts raw logits to calibrated probabilities summing to 1.0."""
        return softmax(np.asarray(logits, dtype=float), temperature=self.temperature)

    def save(self, path: Path | str = DEFAULT_TEMPERATURE_PATH) -> Path:
        """Saves temperature calibration metadata to JSON file."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "model": "fomc_roberta",
            "temperature": round(self.temperature, 6),
            "ece_pre": round(self.ece_pre, 6) if self.ece_pre is not None else None,
            "ece_post": round(self.ece_post, 6) if self.ece_post is not None else None,
            "ece_target": 0.10,
            "meets_target": bool(self.ece_post is not None and self.ece_post <= 0.10),
            "n_samples": self.n_samples,
            "fitted_at": self.fitted_at.isoformat() if self.fitted_at else None,
            "schema_version": "1.0",
        }

        p.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return p

    @classmethod
    def load(cls, path: Path | str = DEFAULT_TEMPERATURE_PATH) -> "TemperatureScaler":
        """Loads temperature parameter from JSON file."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Temperature file not found at: {p}")

        data = json.loads(p.read_text(encoding="utf-8"))
        scaler = cls(temperature=data["temperature"])
        scaler.ece_pre = data.get("ece_pre")
        scaler.ece_post = data.get("ece_post")
        scaler.n_samples = data.get("n_samples")
        if data.get("fitted_at"):
            try:
                scaler.fitted_at = datetime.fromisoformat(data["fitted_at"])
            except ValueError:
                scaler.fitted_at = None
        return scaler
