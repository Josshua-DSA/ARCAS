"""Aggregates article impacts into daily sentiment series."""

from collections import defaultdict
from datetime import date
from typing import Optional

from backend.src.schema import DailySentiment, TargetImpact


class DailyAggregator:
    """Computes daily mean and weighted sentiment per target."""

    @staticmethod
    def aggregate_for_asset_date(
        asset_id: str,
        trading_date: date,
        impacts: list[TargetImpact],
        version: str = "v1",
    ) -> DailySentiment:
        """
        Aggregates impacts for a single asset on a given trading date.
        Strict invariant: If no impacts exist (n_articles == 0),
        score_mean must be None (representing NaN), has_news = False.
        """
        if not impacts:
            return DailySentiment(
                asset_id=asset_id,
                date=trading_date,
                score_mean=None,
                score_weighted=None,
                n_articles=0,
                n_sources=0,
                has_news=False,
                version=version,
            )

        n_articles = len(impacts)
        scores = [imp.score for imp in impacts]
        confidences = [imp.confidence for imp in impacts]

        score_mean = sum(scores) / n_articles

        total_conf = sum(confidences)
        if total_conf > 0:
            score_weighted = sum(s * c for s, c in zip(scores, confidences)) / total_conf
        else:
            score_weighted = score_mean

        return DailySentiment(
            asset_id=asset_id,
            date=trading_date,
            score_mean=round(score_mean, 4),
            score_weighted=round(score_weighted, 4),
            n_articles=n_articles,
            n_sources=1,  # Default minimum source count
            has_news=True,
            version=version,
        )

    @classmethod
    def aggregate_batch(
        cls,
        impacts_with_dates: list[tuple[TargetImpact, date]],
        all_assets: set[str],
        all_dates: set[date],
        version: str = "v1",
    ) -> list[DailySentiment]:
        """
        Aggregates batch of impacts, explicitly creating empty records
        with score_mean=None for dates without news.
        """
        grouped: dict[tuple[str, date], list[TargetImpact]] = defaultdict(list)
        for impact, dt in impacts_with_dates:
            grouped[(impact.asset_id, dt)].append(impact)

        results: list[DailySentiment] = []
        for asset in all_assets:
            for dt in all_dates:
                daily_impacts = grouped.get((asset, dt), [])
                results.append(
                    cls.aggregate_for_asset_date(
                        asset_id=asset,
                        trading_date=dt,
                        impacts=daily_impacts,
                        version=version,
                    )
                )

        return results
