from pydantic import BaseModel, Field


class CandlestickSnapshot(BaseModel):
    end_period_ts: int
    open_dollars: str | None = None
    high_dollars: str | None = None
    low_dollars: str | None = None
    close_dollars: str | None = None
    volume_fp: str
    open_interest_fp: str


class MarketHistory(BaseModel):
    ticker: str
    series_ticker: str
    candlestick_count: int
    candlesticks: list[CandlestickSnapshot]


class SeriesHistory(BaseModel):
    series_ticker: str
    markets: list[MarketHistory]


class HistoryResult(BaseModel):
    lookback_days: int
    period_interval: int
    start_ts: int
    end_ts: int
    max_markets_per_series: int
    series: list[SeriesHistory]
    markets_fetched: int = Field(description="Total markets with at least one candlestick")
    markets_failed: list[str] = Field(default_factory=list)
