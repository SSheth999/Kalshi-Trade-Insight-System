import asyncio

from kalshi_python_async import KalshiClient

from app.etl.config import settings
from app.etl.phases.phase_01_discover.models import SeriesCandidate
from app.etl.phases.phase_02_score.fetch_markets import fetch_open_markets_for_series
from app.etl.phases.phase_02_score.models import RankedSeries, SeriesRankingResult
from app.etl.phases.phase_02_score.volatility import aggregate_market_signals, to_ranked
from app.etl.shared.markets_store import MarketsStore


async def _score_one_series(
    client: KalshiClient,
    candidate: SeriesCandidate,
    semaphore: asyncio.Semaphore,
) -> tuple[RankedSeries | None, list]:
    async with semaphore:
        markets = await fetch_open_markets_for_series(client, candidate.ticker)
        await asyncio.sleep(0.15)

    if not markets:
        return None, []

    metrics = aggregate_market_signals(markets)
    if metrics is None:
        return None, markets

    return to_ranked(candidate, metrics), markets


async def score_series(
    client: KalshiClient,
    candidates: list[SeriesCandidate],
    *,
    top_k: int | None = None,
    max_series_to_score: int | None = None,
    concurrency: int | None = None,
    store: MarketsStore | None = None,
) -> tuple[SeriesRankingResult, MarketsStore]:
    """Rank series by price-volatility proxy from open market snapshots."""
    top_k = top_k if top_k is not None else settings.top_volatile_series
    max_series_to_score = (
        max_series_to_score
        if max_series_to_score is not None
        else settings.max_series_to_score
    )
    concurrency = concurrency if concurrency is not None else settings.score_concurrency

    if store is None:
        store = MarketsStore()

    to_score = candidates[:max_series_to_score]
    semaphore = asyncio.Semaphore(concurrency)

    tasks = [_score_one_series(client, candidate, semaphore) for candidate in to_score]
    results = await asyncio.gather(*tasks)

    ranked: list[RankedSeries] = []
    for candidate, (row, markets) in zip(to_score, results, strict=True):
        if markets:
            store.put(candidate.ticker, markets)
        if row is not None:
            ranked.append(row)

    ranked.sort(key=lambda s: s.score, reverse=True)
    skipped = len(to_score) - len(ranked)

    return (
        SeriesRankingResult(
            top_k=top_k,
            series_scored=len(to_score),
            series_skipped_no_open_markets=skipped,
            max_series_to_score=max_series_to_score,
            ranked_series=ranked[:top_k],
        ),
        store,
    )
