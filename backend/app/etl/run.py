from kalshi_python_async import KalshiClient

from app.etl.phases.phase_01_discover import SeriesUniverseResult, discover_series
from app.etl.phases.phase_02_score import SeriesRankingResult, score_series


async def run_etl(
    client: KalshiClient,
    *,
    min_volume: float,
    through: int = 2,
    category: str | None = None,
    top_k: int | None = None,
    max_series_to_score: int | None = None,
    concurrency: int | None = None,
    universe: SeriesUniverseResult | None = None,
) -> tuple[SeriesUniverseResult, SeriesRankingResult | None]:
    """
    Run ETL phases in order.

    through=1 → discover only
    through=2 → discover + score (default)
    """
    if universe is None:
        universe = await discover_series(
            client,
            min_volume=min_volume,
            category=category,
        )

    if through < 2:
        return universe, None

    rankings = await score_series(
        client,
        universe.series,
        top_k=top_k,
        max_series_to_score=max_series_to_score,
        concurrency=concurrency,
    )
    return universe, rankings
