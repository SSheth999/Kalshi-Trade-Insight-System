from collections.abc import Iterator

MAX_TICKERS_PER_BATCH = 100
MAX_CANDLESTICKS_PER_BATCH = 10_000


def candles_per_market(start_ts: int, end_ts: int, period_interval: int) -> int:
    if end_ts <= start_ts:
        return 0
    period_seconds = period_interval * 60
    span = end_ts - start_ts
    return (span + period_seconds - 1) // period_seconds


def max_tickers_per_batch(
    start_ts: int,
    end_ts: int,
    period_interval: int,
    *,
    max_tickers: int = MAX_TICKERS_PER_BATCH,
    max_candles: int = MAX_CANDLESTICKS_PER_BATCH,
) -> int:
    per_market = candles_per_market(start_ts, end_ts, period_interval)
    if per_market <= 0:
        return max_tickers
    by_candle_limit = max_candles // per_market
    if by_candle_limit <= 0:
        return 1
    return min(max_tickers, by_candle_limit)


def iter_time_windows(
    start_ts: int,
    end_ts: int,
    period_interval: int,
    *,
    max_candles: int = MAX_CANDLESTICKS_PER_BATCH,
) -> Iterator[tuple[int, int]]:
    """Yield non-overlapping (start_ts, end_ts) windows within the 10k candlestick limit."""
    period_seconds = period_interval * 60
    window_seconds = max_candles * period_seconds
    t = start_ts

    while t <= end_ts:
        window_end = min(t + window_seconds, end_ts)
        yield t, window_end
        if window_end >= end_ts:
            break
        t = window_end + period_seconds


def chunked(items: list[str], size: int) -> Iterator[list[str]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]
