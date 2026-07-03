import asyncio
import time

from kalshi_python_async import KalshiClient

from app.etl.config import settings
from app.etl.phases.phase_03_collect.models import MarketSnapshot
from app.etl.phases.phase_04_history.models import CandlestickSnapshot
from app.etl.phases.phase_04_history.routing import (
    chunked,
    iter_time_windows,
    max_tickers_per_batch,
)
from app.etl.phases.phase_04_history.serialize import candlestick_to_snapshot
from app.etl.shared.retry import with_retry


async def fetch_candlesticks_for_tickers(
    client: KalshiClient,
    tickers: list[str],
    *,
    start_ts: int,
    end_ts: int,
    period_interval: int,
    include_latest_before_start: bool,
    semaphore: asyncio.Semaphore,
) -> dict[str, list[CandlestickSnapshot]]:
    """Fetch and merge candlesticks for a batch of market tickers."""
    if not tickers:
        return {}

    accumulated: dict[str, list[CandlestickSnapshot]] = {t: [] for t in tickers}

    for window_start, window_end in iter_time_windows(start_ts, end_ts, period_interval):
        batch_limit = max_tickers_per_batch(window_start, window_end, period_interval)

        for ticker_chunk in chunked(tickers, batch_limit):
            async with semaphore:
                response = await with_retry(
                    lambda tc=ticker_chunk, ws=window_start, we=window_end: client.batch_get_market_candlesticks(
                        market_tickers=",".join(tc),
                        start_ts=ws,
                        end_ts=we,
                        period_interval=period_interval,
                        include_latest_before_start=include_latest_before_start,
                    )
                )
                await asyncio.sleep(0.15)

            for market_data in response.markets:
                snapshots = [
                    candlestick_to_snapshot(c) for c in market_data.candlesticks
                ]
                accumulated[market_data.market_ticker].extend(snapshots)

    for ticker in accumulated:
        accumulated[ticker].sort(key=lambda c: c.end_period_ts)

    return accumulated


def select_markets_for_history(
    markets: list[MarketSnapshot],
    *,
    max_markets_per_series: int | None,
) -> list[MarketSnapshot]:
    if max_markets_per_series is None:
        return markets
    ranked = sorted(
        markets,
        key=lambda m: float(m.volume_24h_fp or 0),
        reverse=True,
    )
    return ranked[:max_markets_per_series]
