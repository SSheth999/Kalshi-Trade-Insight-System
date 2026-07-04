"""Process-wide mutable state for the auto-run startup pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from app.api.schemas import IngestResponse

IngestStatus = Literal["pending", "running", "ready", "error"]


@dataclass
class AppState:
    ingest_status: IngestStatus = "pending"
    latest_ingest: "IngestResponse | None" = None
    ingest_error: str | None = None
    ingest_started_at: datetime | None = None
    ingest_completed_at: datetime | None = None


state = AppState()
