from app.etl.phases.phase_02_score.models import SeriesRankingResult
from app.etl.phases.phase_03_collect.models import (
    CollectedMarketsResult,
    MarketSnapshot,
    SeriesMarkets,
)
from app.etl.shared.markets_store import MarketsStore


def _getattr(obj, name: str, default=None):
    return getattr(obj, name, default)


def market_to_snapshot(market) -> MarketSnapshot:
    return MarketSnapshot(
        ticker=market.ticker,
        event_ticker=market.event_ticker,
        title=_getattr(market, "title"),
        status=market.status,
        yes_bid_dollars=market.yes_bid_dollars,
        yes_ask_dollars=market.yes_ask_dollars,
        last_price_dollars=market.last_price_dollars,
        previous_price_dollars=market.previous_price_dollars,
        volume_24h_fp=market.volume_24h_fp,
        open_interest_fp=market.open_interest_fp,
        close_time=market.close_time,
        rules_primary=_getattr(market, "rules_primary"),
        rules_secondary=_getattr(market, "rules_secondary"),
        can_close_early=_getattr(market, "can_close_early"),
        early_close_condition=_getattr(market, "early_close_condition"),
        settlement_timer_seconds=_getattr(market, "settlement_timer_seconds"),
        expected_expiration_time=_getattr(market, "expected_expiration_time"),
    )


def collect_markets(
    rankings: SeriesRankingResult,
    store: MarketsStore,
) -> CollectedMarketsResult:
    """Slice top-K volatile series markets from the in-memory Phase 2 cache."""
    series_out: list[SeriesMarkets] = []

    for ranked in rankings.ranked_series:
        raw = store.get(ranked.ticker)
        series_out.append(
            SeriesMarkets(
                series_ticker=ranked.ticker,
                score=ranked.score,
                market_count=len(raw),
                markets=[market_to_snapshot(m) for m in raw],
            )
        )

    return CollectedMarketsResult(top_k=rankings.top_k, series=series_out)