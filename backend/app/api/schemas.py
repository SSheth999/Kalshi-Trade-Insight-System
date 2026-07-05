from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    through: int = Field(default=4, ge=1, le=4, description="Run through phase N")
    min_volume: float | None = Field(default=None, gt=0)
    top_k: int | None = Field(default=None, ge=1)
    max_series_to_score: int | None = Field(default=None, ge=1)
    concurrency: int | None = Field(default=None, ge=1)
    lookback_days: int | None = Field(default=None, ge=1)
    period_interval: Literal[1, 60, 1440] | None = None
    max_markets_per_series: int | None = Field(default=None, ge=1)
    candlestick_concurrency: int | None = Field(default=None, ge=1)
    persist: bool = Field(
        default=False,
        description="Write JSON artifacts to data/ (universe, rankings, history)",
    )
    persist_db: bool = Field(
        default=False,
        description="Upsert pipeline result into Postgres/Supabase",
    )


class RankedSeriesSummary(BaseModel):
    ticker: str
    title: str
    score: float
    open_market_count: int
    max_1d_move: float
    avg_spread: float
    total_vol24: float


class Phase1Summary(BaseModel):
    min_volume: float
    total_series_fetched: int
    series_passing_volume_filter: int


class Phase2Summary(BaseModel):
    top_k: int
    series_scored: int
    series_skipped_no_open_markets: int
    markets_cached: int
    ranked_series: list[RankedSeriesSummary]


class Phase3Summary(BaseModel):
    top_k: int
    series_count: int
    total_markets: int


class SeriesHistorySummary(BaseModel):
    series_ticker: str
    market_count: int
    candlestick_count: int


class Phase4Summary(BaseModel):
    lookback_days: int
    period_interval: int
    max_markets_per_series: int
    markets_fetched: int
    candlestick_count: int
    markets_failed_count: int
    series: list[SeriesHistorySummary]


class DbLoadSummary(BaseModel):
    run_id: str
    series_upserted: int
    markets_upserted: int
    rankings_inserted: int
    candlesticks_upserted: int


class IngestResponse(BaseModel):
    status: Literal["completed"] = "completed"
    through: int
    duration_seconds: float
    phase_1: Phase1Summary
    phase_2: Phase2Summary | None = None
    phase_3: Phase3Summary | None = None
    phase_4: Phase4Summary | None = None
    artifacts: list[str] = Field(default_factory=list)
    db_load: DbLoadSummary | None = None


class LatestIngestResponse(BaseModel):
    """Cached result of the most recent ingestion run (auto-run on startup, or manually triggered)."""

    status: Literal["pending", "running", "ready", "error"]
    result: IngestResponse | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class MarketRow(BaseModel):
    ticker: str
    event_ticker: str | None = None
    title: str | None = None
    status: str | None = None
    yes_bid_dollars: float | None = None
    yes_ask_dollars: float | None = None
    last_price_dollars: float | None = None
    previous_price_dollars: float | None = None
    volume_24h_fp: float | None = None
    open_interest_fp: float | None = None
    close_time: datetime | None = None


class SeriesMarketsResponse(BaseModel):
    series_ticker: str
    market_count: int
    markets: list[MarketRow]


class EventOutcomeRow(MarketRow):
    outcome_label: str


class EventMarketsResponse(BaseModel):
    event_ticker: str
    title: str | None
    series_ticker: str | None
    outcome_count: int
    outcomes: list[EventOutcomeRow]
