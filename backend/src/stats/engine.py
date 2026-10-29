"""Deterministic statistical engine for sentiment-market association."""

import json
import math
import uuid
from datetime import date
from typing import Any, Optional

import numpy as np
import pandas as pd

try:
    from scipy import stats
except ImportError:  # pragma: no cover
    stats = None

try:
    import statsmodels.api as sm
except ImportError:  # pragma: no cover
    sm = None

from backend.src.schema import StatResult

# Ambang minimum observasi. Di bawah ini, uji apa pun hanya menghasilkan derau:
# korelasi dari <5 titik tidak bisa dibedakan dari kebetulan, dan OLS dengan
# <10 baris tidak punya derajat kebebasan yang cukup untuk galat HAC.
MIN_OBS_OLS = 10
MIN_OBS_GRANGER = 20

CODE_VERSION = "v0.5.0"


class StatEngine:
    """Executes deterministic econometric tests between sentiment and market metrics."""

    @staticmethod
    def frame_from_daily_prices(daily: list[Any], prices: list[Any]) -> pd.DataFrame:
        """Assembles the engine input frame from daily sentiment and price records.

        Inputs are DailySentiment / PriceRecord sequences. Output keeps the
        engine's expected columns: date, close, score_mean merged on date.
        A news-free day keeps score NaN (daily sentiment of news-free days is
        NaN, not 0).
        """
        if not daily or not prices:
            return pd.DataFrame()
        price_df = pd.DataFrame([p.model_dump() for p in prices])
        daily_df = pd.DataFrame([d.model_dump() for d in daily])
        merged = price_df[["date", "close"]].merge(
            daily_df[["date", "score_mean"]],
            on="date",
            how="left",
        )
        merged["close"] = pd.to_numeric(merged["close"], errors="coerce")
        merged["score_mean"] = pd.to_numeric(merged["score_mean"], errors="coerce")
        return merged[["date", "close", "score_mean"]]

    @staticmethod
    def benjamini_hochberg(p_values: list[float], alpha: float = 0.05) -> list[float]:
        """Calculates adjusted p-values using the Benjamini-Hochberg FDR procedure."""
        n = len(p_values)
        if n == 0:
            return []

        sorted_indices = np.argsort(p_values)
        sorted_p = np.array(p_values)[sorted_indices]

        adjusted = np.zeros(n)
        adjusted[-1] = sorted_p[-1]
        for i in range(n - 2, -1, -1):
            val = (n / (i + 1)) * sorted_p[i]
            adjusted[i] = min(adjusted[i + 1], val)

        adjusted = np.clip(adjusted, 0.0, 1.0)
        reordered_adjusted = np.zeros(n)
        reordered_adjusted[sorted_indices] = adjusted
        return reordered_adjusted.tolist()

    @staticmethod
    def _coerce_date(val: Any) -> date:
        if isinstance(val, date):
            return val
        if isinstance(val, str):
            return date.fromisoformat(val)
        if hasattr(val, "date"):
            return val.date()
        return date.today()

    @classmethod
    def compute_spearman_lags(
        cls,
        df: pd.DataFrame,
        asset_id: str,
        max_lag: int = 5,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> list[StatResult]:
        """
        Calculates Spearman rank correlation between sentiment and market return
        across lags 0 to max_lag. Excludes empty/NaN days.
        Expected df columns: ['date', 'score_mean', 'close']
        """
        results: list[StatResult] = []
        if df.empty or "score_mean" not in df.columns or "close" not in df.columns:
            return results

        clean_df = df.dropna(subset=["close"]).copy()
        clean_df["return"] = clean_df["close"].pct_change()
        # Drop rows where score_mean is NaN (Rule: Empty news days = NaN, not 0)
        valid = clean_df.dropna(subset=["score_mean", "return"])

        if len(valid) < 5:
            return results

        p_raw: list[float] = []
        tentative: list[dict] = []

        for lag in range(max_lag + 1):
            shifted_sentiment = valid["score_mean"].shift(lag)
            sub = pd.DataFrame({"sent": shifted_sentiment, "ret": valid["return"]}).dropna()
            if len(sub) < 5:
                continue

            if stats is not None:
                corr, p_val = stats.spearmanr(sub["sent"], sub["ret"])
                corr = float(corr) if not np.isnan(corr) else 0.0
                p_val = float(p_val) if not np.isnan(p_val) else 1.0
            else:
                # Rank correlation fallback using pandas
                sent_s = pd.Series(sub["sent"], dtype=float)
                ret_s = pd.Series(sub["ret"], dtype=float)
                corr_val = sent_s.corr(ret_s, method="spearman")
                corr = float(corr_val) if pd.notna(corr_val) else 0.0
                p_val = 0.05

            p_raw.append(p_val)
            tentative.append({
                "lag": lag,
                "estimate": corr,
                "p_value": p_val,
                "n_obs": len(sub),
            })

        p_adjusted = cls.benjamini_hochberg(p_raw)

        run_id = str(uuid.uuid4())[:8]
        p_start_raw = period_start if period_start else valid["date"].min()
        p_end_raw = period_end if period_end else valid["date"].max()
        p_start = cls._coerce_date(p_start_raw)
        p_end = cls._coerce_date(p_end_raw)

        for i, item in enumerate(tentative):
            results.append(
                StatResult(
                    run_id=run_id,
                    asset_id=asset_id,
                    test="spearman",
                    market_metric="return",
                    lag=item["lag"],
                    estimate=round(item["estimate"], 4),
                    ci_low=None,
                    ci_high=None,
                    p_value=round(item["p_value"], 5),
                    p_adjusted=round(p_adjusted[i], 5),
                    n_obs=item["n_obs"],
                    period_start=p_start,
                    period_end=p_end,
                    params_json=json.dumps({"method": "spearman", "lag": item["lag"]}),
                    code_version="v0.5.0",
                )
            )

        return results

    @staticmethod
    def _clean_frame(df: pd.DataFrame) -> pd.DataFrame:
        """Frame bersih: terurut tanggal, kolom `return`, tanpa baris kosong.

        Sentimen hari tanpa berita bernilai NaN dan HARUS dibuang, bukan diisi 0.
        Mengisi 0 akan menciptakan "hari netral" palsu dan meredam koefisien.
        """
        if df.empty or not {"date", "close", "score_mean"}.issubset(df.columns):
            return pd.DataFrame()

        out = df.copy()
        out["close"] = pd.to_numeric(out["close"], errors="coerce")
        out["score_mean"] = pd.to_numeric(out["score_mean"], errors="coerce")
        out = out.sort_values("date").reset_index(drop=True)
        out["return"] = out["close"].pct_change()
        return out.dropna(subset=["score_mean", "return"]).reset_index(drop=True)

    @staticmethod
    def _newey_west_lags(n_obs: int) -> int:
        """Aturan bandwidth Newey-West: floor(4 * (n/100) ** (2/9))."""
        if n_obs <= 0:
            return 0
        return max(1, math.floor(4 * (n_obs / 100) ** (2 / 9)))

    @classmethod
    def compute_ols_hac(
        cls,
        df: pd.DataFrame,
        asset_id: str,
        max_lag: int = 5,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> list[StatResult]:
        """Regresi OLS `return ~ sentiment` dengan galat standar Newey-West (HAC).

        Satu regresi per lag (0..max_lag), bukan satu regresi berganda, agar
        tiap lag bisa dibandingkan langsung dengan hasil Spearman dan dikoreksi
        bersama lewat Benjamini-Hochberg.

        HAC dipakai karena deret return pasar hampir selalu heteroskedastik dan
        autokorelasi; galat OLS biasa akan melaporkan p-value yang terlalu kecil.
        """
        results: list[StatResult] = []
        if sm is None:  # pragma: no cover - lingkungan tanpa statsmodels
            return results

        clean = cls._clean_frame(df)
        if len(clean) < MIN_OBS_OLS:
            return results

        p_raw: list[float] = []
        tentative: list[dict[str, Any]] = []

        for lag in range(max_lag + 1):
            x = clean["score_mean"].shift(lag)
            sub = pd.DataFrame({"x": x, "y": clean["return"]}).dropna()
            if len(sub) < MIN_OBS_OLS:
                continue

            nw = cls._newey_west_lags(len(sub))
            try:
                model = sm.OLS(sub["y"], sm.add_constant(sub["x"])).fit(
                    cov_type="HAC", cov_kwds={"maxlags": nw}
                )
            except Exception:  # pragma: no cover - matriks singular
                continue

            coef = float(model.params.iloc[1])
            p_val = float(model.pvalues.iloc[1])
            if not np.isfinite(coef) or not np.isfinite(p_val):
                continue
            ci = model.conf_int()
            lo, hi = float(ci.iloc[1, 0]), float(ci.iloc[1, 1])

            p_raw.append(p_val)
            tentative.append(
                {
                    "lag": lag,
                    "coef": coef,
                    "ci_low": lo,
                    "ci_high": hi,
                    "p_value": p_val,
                    "n_obs": len(sub),
                    "nw_lags": nw,
                    "r2": float(model.rsquared),
                }
            )

        if not tentative:
            return results

        p_adj = cls.benjamini_hochberg(p_raw)
        run_id = str(uuid.uuid4())[:8]
        p_start = cls._coerce_date(period_start or clean["date"].min())
        p_end = cls._coerce_date(period_end or clean["date"].max())

        for i, item in enumerate(tentative):
            results.append(
                StatResult(
                    run_id=run_id,
                    asset_id=asset_id,
                    test="ols",
                    market_metric="return",
                    lag=item["lag"],
                    estimate=round(item["coef"], 6),
                    ci_low=round(item["ci_low"], 6),
                    ci_high=round(item["ci_high"], 6),
                    p_value=round(item["p_value"], 6),
                    p_adjusted=round(p_adj[i], 6),
                    n_obs=item["n_obs"],
                    period_start=p_start,
                    period_end=p_end,
                    params_json=json.dumps(
                        {
                            "method": "ols_newey_west",
                            "lag": item["lag"],
                            "nw_lags": item["nw_lags"],
                            "r2": round(item["r2"], 4),
                        }
                    ),
                    code_version=CODE_VERSION,
                )
            )

        return results

    @classmethod
    def compute_granger(
        cls,
        df: pd.DataFrame,
        asset_id: str,
        max_lag: int = 5,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
    ) -> list[StatResult]:
        """Uji kausalitas Granger: apakah sentimen membantu memprediksi return.

        Arah uji: sentimen -> return. Data dipotong ke baris berpasangan utuh
        (tanpa NaN) karena uji ini memerlukan deret kontinu; lubang di tengah
        deret akan membuat lag bergeser diam-diam.
        """
        results: list[StatResult] = []
        if sm is None:  # pragma: no cover
            return results

        try:
            from statsmodels.tsa.stattools import grangercausalitytests
        except ImportError:  # pragma: no cover
            return results

        clean = cls._clean_frame(df)
        if len(clean) < MIN_OBS_GRANGER:
            return results

        pairs = clean[["return", "score_mean"]].astype(float).dropna()
        # Butuh ruang untuk lag: n harus jauh melebihi maxlag.
        effective_lag = min(max_lag, max(1, len(pairs) // 5))
        if len(pairs) < max(MIN_OBS_GRANGER, effective_lag * 4 + 4):
            return results

        try:
            raw = grangercausalitytests(pairs, maxlag=effective_lag)
        except Exception:  # pragma: no cover - deret konstan / singular
            return results

        p_raw: list[float] = []
        tentative: list[dict[str, Any]] = []
        for lag in sorted(raw.keys()):
            ssr = raw[lag][0].get("ssr_ftest")
            if not ssr:
                continue
            f_stat, p_val = float(ssr[0]), float(ssr[1])
            if not np.isfinite(p_val) or not np.isfinite(f_stat):
                continue
            p_raw.append(p_val)
            tentative.append({"lag": int(lag), "f": f_stat, "p_value": p_val})

        if not tentative:
            return results

        p_adj = cls.benjamini_hochberg(p_raw)
        run_id = str(uuid.uuid4())[:8]
        p_start = cls._coerce_date(period_start or clean["date"].min())
        p_end = cls._coerce_date(period_end or clean["date"].max())

        for i, item in enumerate(tentative):
            results.append(
                StatResult(
                    run_id=run_id,
                    asset_id=asset_id,
                    test="granger",
                    market_metric="return",
                    lag=item["lag"],
                    # `estimate` menyimpan statistik F (bukan koefisien); arah
                    # kausal tidak punya tanda, jadi F selalu >= 0.
                    estimate=round(item["f"], 6),
                    ci_low=None,
                    ci_high=None,
                    p_value=round(item["p_value"], 6),
                    p_adjusted=round(p_adj[i], 6),
                    n_obs=len(pairs),
                    period_start=p_start,
                    period_end=p_end,
                    params_json=json.dumps(
                        {"method": "granger", "lag": item["lag"], "direction": "sentiment->return"}
                    ),
                    code_version=CODE_VERSION,
                )
            )

        return results

    @classmethod
    def compute_car_event_study(
        cls,
        df: pd.DataFrame,
        asset_id: str,
        spike_threshold: float = 0.5,
        window_pre: int = 1,
        window_post: int = 3,
    ) -> list[StatResult]:
        """
        Event study: Cumulative Abnormal Returns (CAR) around sentiment spikes.

        CAR di sini adalah jumlah return pada jendela event, bukan return
        dikurangi benchmark: benchmark per aset belum tersimpan di DB. Karena
        itu pembaca tidak boleh membacanya sebagai alpha.
        """
        if df.empty or len(df) < MIN_OBS_OLS:
            return []

        clean_df = df.dropna(subset=["close"]).copy()
        # reset_index: `.index` adalah LABEL, bukan posisi. Tanpa ini, satu
        # baris NaN yang dibuang membuat .iloc membaca posisi yang salah dan
        # jendela event bergeser tanpa error.
        clean_df = clean_df.reset_index(drop=True)
        clean_df["return"] = clean_df["close"].pct_change()

        # Posisi baris spike, bukan label indeksnya.
        spike_pos = np.flatnonzero(
            clean_df["score_mean"].abs().fillna(0.0).to_numpy() >= spike_threshold
        )

        car_estimates: list[float] = []
        for pos in spike_pos:
            start_i = max(0, int(pos) - window_pre)
            end_i = min(len(clean_df), int(pos) + window_post + 1)
            event_returns = clean_df.iloc[start_i:end_i]["return"].dropna()
            if not event_returns.empty:
                car_estimates.append(float(event_returns.sum()))

        if not car_estimates:
            return []

        mean_car = float(np.mean(car_estimates))
        p_val = 1.0
        ci_low: Optional[float] = None
        ci_high: Optional[float] = None

        # CI hanya bila ada >=2 event dan galat bakunya terdefinisi. n=1 tidak
        # punya sebaran, jadi CI dibiarkan None alih-alih dikarang.
        if stats is not None and len(car_estimates) > 1:
            p_val = float(stats.ttest_1samp(car_estimates, 0.0)[1])
            se = float(np.std(car_estimates, ddof=1) / math.sqrt(len(car_estimates)))
            if se > 0:
                t_crit = float(stats.t.ppf(0.975, len(car_estimates) - 1))
                ci_low = round(mean_car - t_crit * se, 4)
                ci_high = round(mean_car + t_crit * se, 4)

        p_start = cls._coerce_date(df["date"].min())
        p_end = cls._coerce_date(df["date"].max())

        return [
            StatResult(
                run_id=str(uuid.uuid4())[:8],
                asset_id=asset_id,
                test="event_study",
                market_metric="abnormal_return",
                lag=None,
                estimate=round(mean_car, 4),
                ci_low=ci_low,
                ci_high=ci_high,
                p_value=round(p_val, 5),
                p_adjusted=round(p_val, 5),
                n_obs=len(car_estimates),
                period_start=p_start,
                period_end=p_end,
                params_json=json.dumps(
                    {
                        "window_pre": window_pre,
                        "window_post": window_post,
                        "spike_threshold": spike_threshold,
                    }
                ),
                code_version="v0.5.0",
            )
        ]
