"""CAR event study: tersambung ke CLI, jendela memakai posisi, CI tidak dikarang."""

import numpy as np
import pandas as pd

from backend.src.stats.engine import MIN_OBS_OLS, StatEngine


def _frame(closes, scores):
    n = len(closes)
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=n, freq="D"),
            "close": closes,
            "score_mean": scores,
        }
    )


def _closes_with_one_spike(n=30, jump_at=15, jump=0.05):
    """Return harian nol kecuali satu hari, supaya CAR bisa dihitung tangan."""
    closes = [100.0]
    for i in range(1, n):
        closes.append(closes[-1] * (1.0 + (jump if i == jump_at else 0.0)))
    return closes


def test_car_returns_empty_without_spikes():
    frame = _frame(_closes_with_one_spike(), [0.1] * 30)
    assert StatEngine.compute_car_event_study(frame, "XAU") == []


def test_car_requires_minimum_rows():
    frame = _frame([100.0] * (MIN_OBS_OLS - 1), [0.9] * (MIN_OBS_OLS - 1))
    assert StatEngine.compute_car_event_study(frame, "XAU") == []


def test_car_window_uses_positions_not_labels():
    """Satu baris close NaN di depan tidak boleh menggeser jendela event.

    Dulu fungsi memakai `.index` (label) sebagai argumen `.iloc` (posisi).
    Setelah dropna, label != posisi, sehingga CAR dihitung dari hari yang salah.
    """
    n = 30
    closes = _closes_with_one_spike(n, jump_at=15, jump=0.05)
    scores = [0.0] * n
    scores[15] = 0.9  # satu spike

    bersih = _frame(closes, scores)
    hasil_bersih = StatEngine.compute_car_event_study(bersih, "XAU")
    assert len(hasil_bersih) == 1

    # Sisipkan baris dengan close NaN di awal: posisi bergeser satu.
    kotor = pd.concat(
        [pd.DataFrame({"date": [pd.Timestamp("2025-12-31")], "close": [np.nan],
                       "score_mean": [np.nan]}), bersih],
        ignore_index=True,
    )
    hasil_kotor = StatEngine.compute_car_event_study(kotor, "XAU")

    assert len(hasil_kotor) == 1
    assert hasil_kotor[0].n_obs == hasil_bersih[0].n_obs
    assert abs(hasil_kotor[0].estimate - hasil_bersih[0].estimate) < 1e-9


def test_car_single_event_has_no_ci():
    """n=1 tidak punya sebaran: CI harus None, bukan angka karangan."""
    closes = _closes_with_one_spike(30, jump_at=15, jump=0.05)
    scores = [0.0] * 30
    scores[15] = 0.9
    out = StatEngine.compute_car_event_study(_frame(closes, scores), "XAU")

    assert len(out) == 1
    assert out[0].n_obs == 1
    assert out[0].ci_low is None
    assert out[0].ci_high is None
    assert out[0].p_value == 1.0  # tidak ada uji yang bisa dijalankan


def test_car_multiple_events_produce_ci_around_estimate():
    closes = _closes_with_one_spike(40, jump_at=10, jump=0.03)
    scores = [0.0] * 40
    scores[10] = 0.9
    scores[25] = -0.9

    out = StatEngine.compute_car_event_study(_frame(closes, scores), "XAU")

    assert len(out) == 1
    row = out[0]
    assert row.n_obs == 2
    assert row.ci_low is not None and row.ci_high is not None
    assert row.ci_low <= row.estimate <= row.ci_high
    assert "spike_threshold" in row.params_json


def test_car_params_record_window():
    closes = _closes_with_one_spike(30, jump_at=15, jump=0.05)
    scores = [0.0] * 30
    scores[15] = 0.9
    out = StatEngine.compute_car_event_study(_frame(closes, scores), "XAU")
    assert '"window_pre": 1' in out[0].params_json
    assert '"window_post": 3' in out[0].params_json
