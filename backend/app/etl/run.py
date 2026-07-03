from dataclasses import dataclass, field

from kalshi_python_async import KalshiClient

from app.etl.phases.phase_01_discover import SeriesUniverseResult, discover_series
from app.etl.phases.phase_02_score import SeriesRankingResult, score_series
from app.etl.phases.phase_03_collect import CollectedMarketsResult, collect_markets
from app.etl.phases.phase_04_history import HistoryResult, fetch_history
from app.etl.shared.markets_store import MarketsStore


@dataclass
class PipelineResult:
    universe: SeriesUniverseResult
    rankings: SeriesRankingResult | None = None
    collected: CollectedMarketsResult | None = None
    history: HistoryResult | None = None
    markets_store: MarketsStore = field(default_factory=MarketsStore)


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
    lookback_days: int | None = None,
    period_interval: int | None = None,
    max_markets_per_series: int | None = None,
    candlestick_concurrency: int | None = None,
) -> PipelineResult:
    """
    Run ETL phases in order.

    through=1 → discover only
    through=2 → discover + score
    through=3 → through 2 + collect markets (in-memory store)
    through=4 → through 3 + fetch candlestick history
    """
    if universe is None:
        universe = await discover_series(
            client,
            min_volume=min_volume,
            category=category,
        )

    if through < 2:
        return PipelineResult(universe=universe)

    rankings, markets_store = await score_series(
        client,
        universe.series,
        top_k=top_k,
        max_series_to_score=max_series_to_score,
        concurrency=concurrency,
    )

    if through < 3:
        return PipelineResult(
            universe=universe,
            rankings=rankings,
            markets_store=markets_store,
        )

    collected = collect_markets(rankings, markets_store)

    if through < 4:
        return PipelineResult(
            universe=universe,
            rankings=rankings,
            collected=collected,
            markets_store=markets_store,
        )

    history = await fetch_history(
        client,
        collected,
        lookback_days=lookback_days,
        period_interval=period_interval,
        max_markets_per_series=max_markets_per_series,
        concurrency=candlestick_concurrency,
    )

    return PipelineResult(
        universe=universe,
        rankings=rankings,
        collected=collected,
        history=history,
        markets_store=markets_store,
    )
