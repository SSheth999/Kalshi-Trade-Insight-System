import asyncio
import time

from kalshi_python_async import KalshiClient

from app.etl.config import settings
from app.etl.phases.phase_03_collect.models import CollectedMarketsResult
from app.etl.phases.phase_04_history.fetch_candlesticks import (
    fetch_candlesticks_for_tickers,
    select_markets_for_history,
)
from app.etl.phases.phase_04_history.models import (
    HistoryResult,
    MarketHistory,
    SeriesHistory,
)


async def fetch_history(
    client: KalshiClient,
    collected: CollectedMarketsResult,
    *,
    lookback_days: int | None = None,
    period_interval: int | None = None,
    max_markets_per_series: int | None = None,
    concurrency: int | None = None,
    include_latest_before_start: bool | None = None,
) -> HistoryResult:
    lookback_days = (
        lookback_days if lookback_days is not None else settings.lookback_days
    )
    period_interval = (
        period_interval if period_interval is not None else settings.period_interval
    )
    max_markets_per_series = (
        max_markets_per_series
        if max_markets_per_series is not None
        else settings.max_markets_per_series
    )
    concurrency = (
        concurrency
        if concurrency is not None
        else settings.candlestick_concurrency
    )
    include_latest_before_start = (
        include_latest_before_start
        if include_latest_before_start is not None
        else settings.include_latest_before_start
    )

    end_ts = int(time.time())
    start_ts = end_ts - lookback_days * 86400

    semaphore = asyncio.Semaphore(concurrency)
    series_histories: list[SeriesHistory] = []
    markets_fetched = 0
    markets_failed: list[str] = []

    for series in collected.series:
        selected = select_markets_for_history(
            series.markets,
            max_markets_per_series=max_markets_per_series,
        )
        tickers = [m.ticker for m in selected]

        by_ticker = await fetch_candlesticks_for_tickers(
            client,
            tickers,
            start_ts=start_ts,
            end_ts=end_ts,
            period_interval=period_interval,
            include_latest_before_start=include_latest_before_start,
            semaphore=semaphore,
        )

        market_histories: list[MarketHistory] = []
        for market in selected:
            candles = by_ticker.get(market.ticker, [])
            if candles:
                markets_fetched += 1
            else:
                markets_failed.append(market.ticker)

            market_histories.append(
                MarketHistory(
                    ticker=market.ticker,
                    series_ticker=series.series_ticker,
                    candlestick_count=len(candles),
                    candlesticks=candles,
                )
            )

        series_histories.append(
            SeriesHistory(
                series_ticker=series.series_ticker,
                markets=market_histories,
            )
        )

    return HistoryResult(
        lookback_days=lookback_days,
        period_interval=period_interval,
        start_ts=start_ts,
        end_ts=end_ts,
        max_markets_per_series=max_markets_per_series,
        series=series_histories,
        markets_fetched=markets_fetched,
        markets_failed=markets_failed,
    )
