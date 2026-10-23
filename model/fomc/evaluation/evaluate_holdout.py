"""Holdout evaluation and Component Necessity Test (McNemar Test & Bootstrap CI).

Reference:
    Shah, A., Paturi, S., & Chava, S. (2023). ACL 2023.

Evaluates Baseline TF-IDF + LR vs FOMC-RoBERTa on the official 495 unseen test holdout sentences.
Saves official metrics report to model/fomc/evaluation/benchmark_results.json.

Usage:
    python -m model.fomc.evaluation.evaluate_holdout
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score

from model.fomc.src.calibrator import compute_multiclass_ece
from model.fomc.src.data_loader import (
    DEFAULT_FOMC_TEST_PATH,
    get_fomc_texts_and_labels,
    load_fomc_test_holdout,
)
from model.fomc.src.model import DEFAULT_FOMC_BASELINE_PATH, FOMCRoBERTaSentiment

DEFAULT_BENCHMARK_OUT = Path("model/fomc/evaluation/benchmark_results.json")


def compute_mcnemar_test(
    y_true: Sequence[int],
    y_pred_base: Sequence[int],
    y_pred_roberta: Sequence[int],
) -> dict:
    """Computes McNemar's test on 2x2 contingency table with Edwards' continuity correction.

    Contingency Table:
        n00: both wrong
        n01: baseline wrong, roberta correct
        n10: baseline correct, roberta wrong
        n11: both correct
    """
    from scipy.stats import chi2

    y_t = np.asarray(y_true)
    b_correct = (np.asarray(y_pred_base) == y_t)
    r_correct = (np.asarray(y_pred_roberta) == y_t)

    n00 = int(np.sum(~b_correct & ~r_correct))
    n01 = int(np.sum(~b_correct & r_correct))
    n10 = int(np.sum(b_correct & ~r_correct))
    n11 = int(np.sum(b_correct & r_correct))

    discordant = n01 + n10
    if discordant == 0:
        chi2_stat = 0.0
        p_val = 1.0
    else:
        # Edwards' continuity correction
        chi2_stat = float(((abs(n01 - n10) - 1.0) ** 2) / discordant)
        p_val = float(chi2.sf(chi2_stat, df=1))

    return {
        "contingency_table": {
            "both_correct_n11": n11,
            "both_wrong_n00": n00,
            "baseline_correct_roberta_wrong_n10": n10,
            "roberta_correct_baseline_wrong_n01": n01,
        },
        "chi2_statistic": round(chi2_stat, 4),
        "p_value": round(p_val, 6),
        "significant_p_05": p_val < 0.05,
        "component_adopted": p_val < 0.05 and n01 > n10,
    }


def compute_bootstrap_ci(
    y_true: Sequence[int],
    y_pred_base: Sequence[int],
    y_pred_roberta: Sequence[int],
    n_bootstraps: int = 1000,
    seed: int = 5768,
) -> dict:
    """Computes 95% Bootstrap Confidence Interval for difference in Macro F1 score."""
    rng = np.random.RandomState(seed)
    y_t = np.asarray(y_true)
    y_b = np.asarray(y_pred_base)
    y_r = np.asarray(y_pred_roberta)
    n = len(y_t)

    delta_f1s = []
    for _ in range(n_bootstraps):
        idx = rng.randint(0, n, size=n)
        f1_b = f1_score(y_t[idx], y_b[idx], average="macro", zero_division=0)
        f1_r = f1_score(y_t[idx], y_r[idx], average="macro", zero_division=0)
        delta_f1s.append(f1_r - f1_b)

    delta_f1s = np.array(delta_f1s)
    ci_lower = float(np.percentile(delta_f1s, 2.5))
    ci_upper = float(np.percentile(delta_f1s, 97.5))
    mean_delta = float(np.mean(delta_f1s))

    return {
        "n_bootstraps": n_bootstraps,
        "mean_delta_macro_f1": round(mean_delta, 4),
        "ci_95_lower": round(ci_lower, 4),
        "ci_95_upper": round(ci_upper, 4),
        "ci_strictly_positive": ci_lower > 0.0,
    }


def evaluate_holdout(
    test_path: Path | str = DEFAULT_FOMC_TEST_PATH,
    baseline_path: Path | str = DEFAULT_FOMC_BASELINE_PATH,
    out_path: Path | str = DEFAULT_BENCHMARK_OUT,
    skip_roberta_if_missing: bool = False,
) -> dict:
    """Evaluates Baseline vs RoBERTa on 495 test sentences and exports benchmark report."""
    df_test = load_fomc_test_holdout(test_path)
    texts, y_true = get_fomc_texts_and_labels(df_test)
    n_test = len(texts)

    # 1. Evaluate Baseline Model
    b_path = Path(baseline_path)
    if not b_path.exists():
        raise FileNotFoundError(
            f"Trained baseline not found at {b_path}. Run training first via model.fomc.src.model."
        )

    baseline_data = joblib.load(b_path)
    X_test = baseline_data["vectorizer"].transform(texts)
    y_pred_base = baseline_data["classifier"].predict(X_test).tolist()
    probs_base = baseline_data["classifier"].predict_proba(X_test)

    metrics_base = {
        "accuracy": round(float(accuracy_score(y_true, y_pred_base)), 4),
        "f1_macro": round(float(f1_score(y_true, y_pred_base, average="macro")), 4),
        "cohen_kappa": round(float(cohen_kappa_score(y_true, y_pred_base)), 4),
        "ece": round(compute_multiclass_ece(probs_base, y_true), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred_base).tolist(),
    }

    report = {
        "dataset": "FOMC Trillion Dollar Words (split-combine-5768)",
        "test_samples": n_test,
        "baseline_tfidf_lr": metrics_base,
    }

    # 2. Evaluate FOMC-RoBERTa Model (if available)
    try:
        roberta = FOMCRoBERTaSentiment()
        raw_logits = roberta.predict_raw_logits(texts)
        probs_roberta = roberta.calibrator.predict_proba(raw_logits)
        y_pred_roberta = np.argmax(probs_roberta, axis=-1).tolist()

        metrics_roberta = {
            "accuracy": round(float(accuracy_score(y_true, y_pred_roberta)), 4),
            "f1_macro": round(float(f1_score(y_true, y_pred_roberta, average="macro")), 4),
            "cohen_kappa": round(float(cohen_kappa_score(y_true, y_pred_roberta)), 4),
            "ece": round(compute_multiclass_ece(probs_roberta, y_true), 4),
            "calibrated_temperature": roberta.calibrator.temperature,
            "confusion_matrix": confusion_matrix(y_true, y_pred_roberta).tolist(),
        }

        # 3. Statistical Testing: McNemar & Bootstrap
        mcnemar_results = compute_mcnemar_test(y_true, y_pred_base, y_pred_roberta)
        bootstrap_results = compute_bootstrap_ci(y_true, y_pred_base, y_pred_roberta)

        report["fomc_roberta"] = metrics_roberta
        report["component_necessity_test"] = {
            "mcnemar": mcnemar_results,
            "bootstrap_ci": bootstrap_results,
        }

    except Exception as exc:
        if skip_roberta_if_missing:
            report["fomc_roberta"] = {"status": "skipped", "reason": str(exc)}
        else:
            raise exc

    # 4. Save to JSON
    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    report["saved_to"] = str(out_p)

    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate holdout benchmark for Track FOMC.")
    parser.add_argument("--test", type=Path, default=DEFAULT_FOMC_TEST_PATH)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_FOMC_BASELINE_PATH)
    parser.add_argument("--out", type=Path, default=DEFAULT_BENCHMARK_OUT)
    args = parser.parse_args(argv)

    results = evaluate_holdout(test_path=args.test, baseline_path=args.baseline, out_path=args.out)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
