from pydantic import BaseModel, Field


class SeriesVolatilityMetrics(BaseModel):
    avg_spread: float = Field(description="Mean yes_ask - yes_bid across open markets")
    max_1d_move: float = Field(description="Max abs(last - previous) across open markets")
    mean_1d_move: float = Field(description="Mean abs(last - previous) across open markets")
    total_vol24: float = Field(description="Sum of volume_24h_fp across open markets")
    open_market_count: int = Field(description="Number of open markets in the series")


class RankedSeries(BaseModel):
    ticker: str
    title: str
    category: str
    frequency: str
    tags: list[str] = Field(default_factory=list)
    volume: float = Field(description="Lifetime series volume from Phase 1")
    score: float
    metrics: SeriesVolatilityMetrics


class SeriesRankingResult(BaseModel):
    top_k: int
    series_scored: int
    series_skipped_no_open_markets: int
    max_series_to_score: int
    ranked_series: list[RankedSeries]
