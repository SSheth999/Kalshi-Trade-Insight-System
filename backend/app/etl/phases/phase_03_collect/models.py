from datetime import datetime

from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    ticker: str
    event_ticker: str
    title: str | None = None
    status: str
    yes_bid_dollars: str
    yes_ask_dollars: str
    last_price_dollars: str
    previous_price_dollars: str
    volume_24h_fp: str
    open_interest_fp: str
    close_time: datetime
    # Rule text — used for resolution risk scoring and embeddings
    rules_primary: str | None = None
    rules_secondary: str | None = None
    # Settlement / close metadata
    can_close_early: bool | None = None
    early_close_condition: str | None = None
    settlement_timer_seconds: int | None = None
    expected_expiration_time: datetime | None = None


class SeriesMarkets(BaseModel):
    series_ticker: str
    score: float
    market_count: int
    markets: list[MarketSnapshot]


class CollectedMarketsResult(BaseModel):
    top_k: int
    series: list[SeriesMarkets]
