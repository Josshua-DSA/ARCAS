"""Evaluation metrics for sentiment models: F1 macro, ECE, Cohen's Kappa.

Fungsi di sini dipakai bersama oleh Track FOMC dan Track XAU. Sebelumnya
`compute_mcnemar_test` dan `compute_bootstrap_ci` hanya hidup di dalam
`model/fomc/evaluation/evaluate_holdout.py` (skrip, bukan modul pustaka),
sehingga padanan XAU-nya tidak pernah diverifikasi. Menempatkannya di sini
membuat satu implementasi dipakai dan diuji untuk kedua track.
"""

from typing import Sequence

import numpy as np

try:
    from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score
except ImportError:  # pragma: no cover
    accuracy_score = None
    cohen_kappa_score = None
    f1_score = None


def compute_ece(probs: Sequence[float], confidences: Sequence[float], true_labels: Sequence[int], n_bins: int = 10) -> float:
    """Computes Expected Calibration Error (ECE) untuk kasus single-label.

    Catatan batas bin: bin terakhir harus memakai `<=` pada batas atas.
    Versi sebelumnya memakai `<` untuk SEMUA bin, sehingga confidence tepat
    1.0 tidak masuk bin mana pun dan dibuang dari perhitungan. Akibatnya model
    yang yakin 100% tetapi selalu salah dilaporkan ECE = 0.0 (sempurna) --
    false negative terburuk untuk metrik kalibrasi. Perilaku ini kini
    disamakan dengan `compute_multiclass_ece` di
    `model/fomc/src/calibrator.py`, yang sudah menangani kasus ini dengan benar
    dan merupakan implementasi yang dipakai laporan evaluasi FOMC/XAU.
    """
    if len(probs) == 0:
        return 0.0

    bins = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(probs)

    for i in range(n_bins):
        bin_lower = bins[i]
        bin_upper = bins[i + 1]
        # Bin terakhir inklusif agar confidence 1.0 tidak terbuang.
        if i == n_bins - 1:
            in_bin = [(c >= bin_lower and c <= bin_upper) for c in confidences]
        else:
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


def compute_mcnemar_test(
    y_true: Sequence[int],
    y_pred_base: Sequence[int],
    y_pred_roberta: Sequence[int],
) -> dict:
    """Uji McNemar pada tabel kontingensi 2x2 dengan koreksi kontinuitas Edwards.

    Tabel kontingensi:
        n00: keduanya salah
        n01: baseline salah, roberta benar
        n10: baseline benar, roberta salah
        n11: keduanya benar

    Koreksi kontinuitas Edwards dipakai karena sampel holdout kecil; tanpa
    koreksi, uji McNemar terlalu agresif menyatakan signifikan pada selisih
    yang tipis.
    """
    from scipy.stats import chi2

    y_t = np.asarray(y_true)
    b_correct = np.asarray(y_pred_base) == y_t
    r_correct = np.asarray(y_pred_roberta) == y_t

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
    """CI 95% bootstrap untuk selisih macro-F1 antara dua model.

    `seed` dikunci agar hasil dapat direproduksi: tanpa itu, laporan evaluasi
    tidak bisa dibandingkan antar run.
    """
    if f1_score is None:  # pragma: no cover
        raise ImportError("scikit-learn dibutuhkan untuk compute_bootstrap_ci")

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

    delta_f1s_arr = np.array(delta_f1s)
    ci_lower = float(np.percentile(delta_f1s_arr, 2.5))
    ci_upper = float(np.percentile(delta_f1s_arr, 97.5))
    mean_delta = float(np.mean(delta_f1s_arr))

    return {
        "n_bootstraps": n_bootstraps,
        "mean_delta_macro_f1": round(mean_delta, 4),
        "ci_95_lower": round(ci_lower, 4),
        "ci_95_upper": round(ci_upper, 4),
        "ci_strictly_positive": ci_lower > 0.0,
    }
