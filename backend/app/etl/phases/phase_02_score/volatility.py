import math
from statistics import mean

from app.etl.phases.phase_01_discover.models import SeriesCandidate
from app.etl.phases.phase_02_score.models import RankedSeries, SeriesVolatilityMetrics

WEIGHT_MAX_1D_MOVE = 0.4
WEIGHT_AVG_SPREAD = 0.3
WEIGHT_LOG_VOL24 = 0.3


def _parse_dollar(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _market_spread(market) -> float | None:
    bid = _parse_dollar(market.yes_bid_dollars)
    ask = _parse_dollar(market.yes_ask_dollars)
    if bid is None or ask is None:
        return None
    return ask - bid


def _market_1d_move(market) -> float | None:
    last = _parse_dollar(market.last_price_dollars)
    previous = _parse_dollar(market.previous_price_dollars)
    if last is None or previous is None:
        return None
    return abs(last - previous)


def _market_vol24(market) -> float:
    return float(market.volume_24h_fp or 0)


def aggregate_market_signals(markets: list) -> SeriesVolatilityMetrics | None:
    if not markets:
        return None

    spreads: list[float] = []
    moves: list[float] = []
    total_vol24 = 0.0

    for market in markets:
        spread = _market_spread(market)
        if spread is not None:
            spreads.append(spread)

        move = _market_1d_move(market)
        if move is not None:
            moves.append(move)

        total_vol24 += _market_vol24(market)

    return SeriesVolatilityMetrics(
        avg_spread=mean(spreads) if spreads else 0.0,
        max_1d_move=max(moves) if moves else 0.0,
        mean_1d_move=mean(moves) if moves else 0.0,
        total_vol24=total_vol24,
        open_market_count=len(markets),
    )


def composite_score(metrics: SeriesVolatilityMetrics) -> float:
    return (
        WEIGHT_MAX_1D_MOVE * metrics.max_1d_move
        + WEIGHT_AVG_SPREAD * metrics.avg_spread
        + WEIGHT_LOG_VOL24 * math.log1p(metrics.total_vol24)
    )


def to_ranked(candidate: SeriesCandidate, metrics: SeriesVolatilityMetrics) -> RankedSeries:
    return RankedSeries(
        ticker=candidate.ticker,
        title=candidate.title,
        category=candidate.category,
        frequency=candidate.frequency,
        tags=candidate.tags,
        volume=candidate.volume,
        score=composite_score(metrics),
        metrics=metrics,
    )
