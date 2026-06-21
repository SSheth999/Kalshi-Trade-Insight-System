from datetime import datetime

from pydantic import BaseModel, Field


class SeriesCandidate(BaseModel):
    ticker: str
    title: str
    category: str
    frequency: str
    tags: list[str] = Field(default_factory=list)
    volume: float = Field(description="Total contracts traded across all events in the series")
    last_updated_ts: datetime | None = None


class SeriesUniverseResult(BaseModel):
    min_volume: float
    total_series_fetched: int
    series_passing_volume_filter: int
    series: list[SeriesCandidate]
