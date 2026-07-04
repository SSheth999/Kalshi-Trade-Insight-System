from pydantic import BaseModel


class MarketTick(BaseModel):
    ticker: str
    series_ticker: str
    last_price_dollars: float | None
    yes_bid_dollars: float | None
    yes_ask_dollars: float | None
    volume_24h_fp: float | None
    open_interest_fp: float | None
    # price delta vs previous poll; None on first poll
    price_delta: float | None = None


class WatcherSnapshot(BaseModel):
    event: str = "snapshot"
    poll_count: int
    tickers: list[MarketTick]


class WatcherStartRequest(BaseModel):
    poll_interval_seconds: float = 30.0
    top_k: int = 20


class WatcherStatus(BaseModel):
    running: bool
    poll_interval_seconds: float | None = None
    top_k: int | None = None
    poll_count: int = 0
    connected_clients: int = 0
