from pydantic import BaseModel


class CandlestickPoint(BaseModel):
    time: int  # unix seconds (end_period_ts) — lightweight-charts time format
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float | None = None
    volume: float | None = None


class CandlesticksResponse(BaseModel):
    ticker: str
    period_interval: int
    candles: list[CandlestickPoint]


class MarketChartTick(BaseModel):
    event: str = "tick"
    ticker: str
    time: int  # unix seconds
    price: float | None
    yes_bid: float | None
    yes_ask: float | None
