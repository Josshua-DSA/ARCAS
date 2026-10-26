"""Tests for T-1: OLS Newey-West HAC dan uji Granger (FR-11).

Fokus uji ini bukan sekadar "tidak crash", tetapi kebenaran statistik:
- koefisien harus memulihkan nilai yang ditanam pada data sintetis,
- Granger harus peka arah (tidak menyala saat kausalitas terbalik),
- koreksi Benjamini-Hochberg harus menyamai implementasi referensi,
- guard harus menolak data yang terlalu sedikit alih-alih mengarang hasil.
"""

import numpy as np
import pandas as pd
import pytest

from backend.src.stats.engine import StatEngine


def _series(n=250, coef=0.0, seed=42, sent_lag=0, lead=0):
    """Bangun (date, close, score_mean) dengan hubungan yang diketahui.

    coef     : kekuatan hubungan.
    lead     : bila > 0, return[t] mengikuti sentimen[t-lead] -- sentimen
               benar-benar MEMIMPIN return (syarat uji Granger). Tanpa `lead`,
               hubungan hanya kontemporer dan Granger memang tidak akan menyala.
    sent_lag : bila > 0, sentimen mengikuti return pada lag tersebut
               (kausalitas terbalik).
    """
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    ret = rng.normal(0, 0.01, n)

    if sent_lag > 0:
        sent = np.zeros(n)
        for t in range(sent_lag, n):
            sent[t] = 0.8 * ret[t - sent_lag] + rng.normal(0, 0.1)
    else:
        sent = rng.normal(0, 1, n)
        if coef and lead > 0:
            # Return hari ini bereaksi terhadap sentimen beberapa hari lalu.
            shifted = np.roll(sent, lead)
            shifted[:lead] = 0.0
            ret = ret + coef * shifted
        elif coef:
            ret = coef * sent + rng.normal(0, 0.01, n)

    close = 100 * np.cumprod(1 + ret)
    return pd.DataFrame({"date": dates, "close": close, "score_mean": sent})


# ---------------------------------------------------------------------------
# OLS HAC
# ---------------------------------------------------------------------------


def test_ols_recovers_planted_coefficient():
    """Koefisien yang ditanam (0.01) harus muncul di interval kepercayaan lag-0."""
    df = _series(n=400, coef=0.01, seed=1)
    results = StatEngine.compute_ols_hac(df, "SPX", max_lag=2)

    assert results, "OLS harus menghasilkan minimal satu baris"
    lag0 = next(r for r in results if r.lag == 0)
    assert lag0.ci_low is not None and lag0.ci_high is not None
    assert lag0.ci_low <= 0.01 <= lag0.ci_high, (
        f"koefisien 0.01 harus di dalam CI [{lag0.ci_low}, {lag0.ci_high}]"
    )
    assert lag0.p_value < 0.01, "hubungan sekuat ini harus sangat signifikan"
    assert lag0.test == "ols"
    assert lag0.market_metric == "return"


def test_ols_reports_hac_not_naive_standard_errors():
    """Galat standar HAC harus tersimpan di params_json bersama bandwidth-nya."""
    df = _series(n=300, coef=0.01, seed=2)
    results = StatEngine.compute_ols_hac(df, "SPX", max_lag=1)

    lag0 = next(r for r in results if r.lag == 0)
    assert "ols_newey_west" in lag0.params_json
    assert "nw_lags" in lag0.params_json
    # Bandwidth Newey-West harus >= 1 untuk deret sepanjang ini.
    assert '"nw_lags": 0' not in lag0.params_json


def test_ols_ci_brackets_estimate():
    """CI harus mengapit estimasi; kalau tidak, ada yang salah di conf_int."""
    df = _series(n=200, coef=0.01, seed=3)
    for r in StatEngine.compute_ols_hac(df, "SPX", max_lag=4):
        assert r.ci_low is not None and r.ci_high is not None
        assert r.ci_low <= r.estimate <= r.ci_high


def test_ols_adjusted_p_is_never_below_raw():
    """BH hanya boleh menaikkan p-value, tidak pernah menurunkannya."""
    df = _series(n=200, coef=0.005, seed=4)
    results = StatEngine.compute_ols_hac(df, "SPX", max_lag=5)
    for r in results:
        assert r.p_adjusted is not None
        assert r.p_adjusted >= r.p_value - 1e-12


def test_ols_empty_on_insufficient_data():
    """Di bawah ambang minimum, kembalikan kosong -- jangan mengarang hasil."""
    df = _series(n=8, coef=0.01, seed=5)
    assert StatEngine.compute_ols_hac(df, "SPX") == []


def test_ols_empty_on_missing_columns():
    df = pd.DataFrame({"date": pd.date_range("2023-01-02", periods=50, freq="B")})
    assert StatEngine.compute_ols_hac(df, "SPX") == []


def test_ols_drops_newsless_days_instead_of_zero_filling():
    """Hari tanpa berita (score_mean NaN) harus dibuang, bukan diisi 0.

    Kalau diisi 0, jumlah observasi akan membengkak dan koefisien teredam.
    """
    df = _series(n=120, coef=0.01, seed=6)
    df.loc[df.index[:40], "score_mean"] = np.nan

    results = StatEngine.compute_ols_hac(df, "SPX", max_lag=0)
    if results:
        assert results[0].n_obs <= 80, "hari NaN tidak boleh ikut dihitung"


# ---------------------------------------------------------------------------
# Granger
# ---------------------------------------------------------------------------


def test_granger_detects_sentiment_leading_returns():
    """Sentimen yang benar-benar memimpin return harus terdeteksi.

    Hubungan dibuat dengan `lead=1`: return[t] bereaksi terhadap sentimen[t-1].
    Ini syarat sebenarnya uji Granger -- korelasi kontemporer saja tidak cukup.
    """
    df = _series(n=300, coef=0.01, seed=7, lead=1)
    results = StatEngine.compute_granger(df, "SPX", max_lag=3)

    assert results, "Granger harus menghasilkan baris"
    assert any(r.p_adjusted is not None and r.p_adjusted < 0.05 for r in results), (
        "kausalitas sentimen->return harus signifikan setelah koreksi BH"
    )


def test_granger_is_direction_sensitive():
    """Kausalitas TERBALIK tidak boleh dilaporkan sebagai sentimen->return."""
    df = _series(n=300, seed=8, sent_lag=2)
    results = StatEngine.compute_granger(df, "SPX", max_lag=3)

    if results:
        assert all(r.p_adjusted is None or r.p_adjusted > 0.01 for r in results), (
            "Granger seharusnya tidak menyala saat arahnya terbalik"
        )


def test_granger_empty_on_insufficient_data():
    df = _series(n=10, seed=9)
    assert StatEngine.compute_granger(df, "SPX") == []


def test_granger_estimate_is_f_statistic():
    """`estimate` menyimpan F, sehingga tidak boleh negatif."""
    df = _series(n=200, coef=0.01, seed=10)
    for r in StatEngine.compute_granger(df, "SPX", max_lag=2):
        assert r.estimate >= 0
        assert r.test == "granger"


# ---------------------------------------------------------------------------
# Benjamini-Hochberg
# ---------------------------------------------------------------------------


def test_benjamini_hochberg_matches_statsmodels_reference():
    """Implementasi sendiri harus identik dengan referensi statsmodels."""
    from statsmodels.stats.multitest import multipletests

    p_values = [0.001, 0.008, 0.039, 0.041, 0.042, 0.06, 0.074, 0.205, 0.212, 0.216]
    ours = StatEngine.benjamini_hochberg(p_values)
    corrected = multipletests(p_values, method="fdr_bh")[1]
    reference = np.asarray(corrected, dtype=float).tolist()

    assert np.allclose(ours, reference), f"BH berbeda dari referensi: {ours} vs {reference}"


def test_benjamini_hochberg_handles_empty():
    assert StatEngine.benjamini_hochberg([]) == []


# ---------------------------------------------------------------------------
# Kebenaran lintas-uji
# ---------------------------------------------------------------------------


def test_no_false_positive_on_independent_series():
    """Deret yang saling bebas tidak boleh lolos setelah koreksi BH.

    Tanpa koreksi, 6 uji per aset membuat peluang false positive ~26%.
    """
    df = _series(n=250, coef=0.0, seed=11)
    ols = StatEngine.compute_ols_hac(df, "SPX", max_lag=5)
    assert not any(r.p_adjusted is not None and r.p_adjusted < 0.01 for r in ols)


@pytest.mark.parametrize("asset", ["XAU", "RATE_UST", "SPX"])
def test_all_locked_universe_assets_run(asset):
    """Ketiga aset di LOCKED_UNIVERSE harus bisa diproses tanpa error."""
    df = _series(n=150, coef=0.01, seed=12)
    assert StatEngine.compute_ols_hac(df, asset, max_lag=2)
    assert StatEngine.compute_granger(df, asset, max_lag=2)
