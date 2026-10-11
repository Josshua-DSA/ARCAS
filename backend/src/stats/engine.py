"""Deterministic statistical engine for sentiment-market association."""

from datetime import date
import json
import uuid
from typing import Any, Optional
import numpy as np
import pandas as pd

try:
    from scipy import stats  # type: ignore
except ImportError:
    stats = None  # type: ignore

from backend.src.schema import StatResult


class StatEngine:
    """Executes deterministic econometric tests between sentiment and market metrics."""

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
        """
        if df.empty or len(df) < 10:
            return []

        clean_df = df.dropna(subset=["close"]).copy()
        clean_df["return"] = clean_df["close"].pct_change()
        spikes = clean_df[clean_df["score_mean"].abs() >= spike_threshold].index

        car_estimates: list[float] = []
        for idx in spikes:
            start_i = max(0, idx - window_pre)
            end_i = min(len(clean_df), idx + window_post + 1)
            event_returns = clean_df.iloc[start_i:end_i]["return"].dropna()
            if not event_returns.empty:
                car = float(event_returns.sum())
                car_estimates.append(car)

        if not car_estimates:
            return []

        mean_car = float(np.mean(car_estimates))
        p_val = 1.0
        if stats is not None and len(car_estimates) > 1:
            p_val = float(stats.ttest_1samp(car_estimates, 0.0)[1])

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
                ci_low=None,
                ci_high=None,
                p_value=round(p_val, 5),
                p_adjusted=round(p_val, 5),
                n_obs=len(car_estimates),
                period_start=p_start,
                period_end=p_end,
                params_json=json.dumps({"window_pre": window_pre, "window_post": window_post}),
                code_version="v0.5.0",
            )
        ]
