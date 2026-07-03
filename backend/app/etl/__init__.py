"""Kalshi ETL pipeline."""

from app.etl.phases.phase_01_discover import discover_series
from app.etl.phases.phase_02_score import score_series
from app.etl.phases.phase_03_collect import collect_markets
from app.etl.phases.phase_04_history import fetch_history
from app.etl.run import PipelineResult, run_etl

__all__ = [
    "collect_markets",
    "discover_series",
    "fetch_history",
    "PipelineResult",
    "run_etl",
    "score_series",
]
