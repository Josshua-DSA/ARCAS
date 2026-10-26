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

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score

from model.common.metrics import compute_bootstrap_ci, compute_mcnemar_test
from model.fomc.src.calibrator import compute_multiclass_ece
from model.fomc.src.data_loader import (
    DEFAULT_FOMC_TEST_PATH,
    get_fomc_texts_and_labels,
    load_fomc_test_holdout,
)
from model.fomc.src.model import DEFAULT_FOMC_BASELINE_PATH, FOMCRoBERTaSentiment

DEFAULT_BENCHMARK_OUT = Path("model/fomc/evaluation/benchmark_results.json")




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
