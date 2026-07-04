import time
from pathlib import Path

from app.api.schemas import (
    DbLoadSummary,
    IngestRequest,
    IngestResponse,
    Phase1Summary,
    Phase2Summary,
    Phase3Summary,
    Phase4Summary,
    RankedSeriesSummary,
    SeriesHistorySummary,
)
from app.etl.config import settings
from app.etl.run import PipelineResult, run_etl
from app.etl.shared import kalshi_client, save_json
from kalshi_python_async import KalshiClient


def _resolve_request(body: IngestRequest) -> dict:
    """Resolve the request parameters."""
    return {
        "min_volume": body.min_volume if body.min_volume is not None else settings.min_series_volume,
        "through": body.through,
        "top_k": body.top_k if body.top_k is not None else settings.top_volatile_series,
        "max_series_to_score": (
            body.max_series_to_score
            if body.max_series_to_score is not None
            else settings.max_series_to_score
        ),
        "concurrency": (
            body.concurrency if body.concurrency is not None else settings.score_concurrency
        ),
        "lookback_days": (
            body.lookback_days if body.lookback_days is not None else settings.lookback_days
        ),
        "period_interval": (
            body.period_interval if body.period_interval is not None else settings.period_interval
        ),
        "max_markets_per_series": (
            body.max_markets_per_series
            if body.max_markets_per_series is not None
            else settings.max_markets_per_series
        ),
        "candlestick_concurrency": (
            body.candlestick_concurrency
            if body.candlestick_concurrency is not None
            else settings.candlestick_concurrency
        ),
    }


def build_ingest_response(
    result: PipelineResult,
    *,
    through: int,
    duration_seconds: float,
    artifacts: list[str] | None = None,
    db_load: DbLoadSummary | None = None,
) -> IngestResponse:
    """Build the ingest result after the pipeline is successfully run. wrapped in the endpoint response."""
    universe = result.universe
    phase_1 = Phase1Summary(
        min_volume=universe.min_volume,
        total_series_fetched=universe.total_series_fetched,
        series_passing_volume_filter=universe.series_passing_volume_filter,
    )

    phase_2: Phase2Summary | None = None
    if result.rankings is not None:
        rankings = result.rankings
        phase_2 = Phase2Summary(
            top_k=rankings.top_k,
            series_scored=rankings.series_scored,
            series_skipped_no_open_markets=rankings.series_skipped_no_open_markets,
            markets_cached=len(result.markets_store),
            ranked_series=[
                RankedSeriesSummary(
                    ticker=s.ticker,
                    title=s.title,
                    score=s.score,
                    open_market_count=s.metrics.open_market_count,
                    max_1d_move=s.metrics.max_1d_move,
                    avg_spread=s.metrics.avg_spread,
                    total_vol24=s.metrics.total_vol24,
                )
                for s in rankings.ranked_series
            ],
        )

    phase_3: Phase3Summary | None = None
    if result.collected is not None:
        phase_3 = Phase3Summary(
            top_k=result.collected.top_k,
            series_count=len(result.collected.series),
            total_markets=sum(s.market_count for s in result.collected.series),
        )

    phase_4: Phase4Summary | None = None
    if result.history is not None:
        history = result.history
        phase_4 = Phase4Summary(
            lookback_days=history.lookback_days,
            period_interval=history.period_interval,
            max_markets_per_series=history.max_markets_per_series,
            markets_fetched=history.markets_fetched,
            candlestick_count=sum(
                m.candlestick_count for s in history.series for m in s.markets
            ),
            markets_failed_count=len(history.markets_failed),
            series=[
                SeriesHistorySummary(
                    series_ticker=s.series_ticker,
                    market_count=len(s.markets),
                    candlestick_count=sum(m.candlestick_count for m in s.markets),
                )
                for s in history.series
            ],
        )

    return IngestResponse(
        through=through,
        duration_seconds=duration_seconds,
        phase_1=phase_1,
        phase_2=phase_2,
        phase_3=phase_3,
        phase_4=phase_4,
        artifacts=artifacts or [],
        db_load=db_load,
    )


def _persist_artifacts(result: PipelineResult, through: int) -> list[str]:
    data_dir = Path(settings.data_dir)
    paths: list[str] = []

    universe_path = data_dir / "series_universe.json"
    save_json(universe_path, result.universe)
    paths.append(str(universe_path.resolve()))

    if through >= 2 and result.rankings is not None:
        rankings_path = data_dir / "series_rankings.json"
        save_json(rankings_path, result.rankings)
        paths.append(str(rankings_path.resolve()))

    if through >= 4 and result.history is not None:
        history_path = data_dir / "candlestick_history.json"
        save_json(history_path, result.history)
        paths.append(str(history_path.resolve()))

    return paths


async def run_ingest(body: IngestRequest) -> IngestResponse:
    params = _resolve_request(body)
    through = params.pop("through")
    min_volume = params.pop("min_volume")
    started = time.perf_counter()

    async with kalshi_client() as client:
        result = await run_etl(
            client,
            min_volume=min_volume,
            through=through,
            **params,
        )

    duration = time.perf_counter() - started

    artifacts: list[str] = []
    if body.persist:
        artifacts = _persist_artifacts(result, through)

    db_load_summary: DbLoadSummary | None = None
    if body.persist_db:
        from app.db.load import load_pipeline_result

        counts = load_pipeline_result(
            result,
            through=through,
            duration_seconds=duration,
            params=_resolve_request(body),
        )
        db_load_summary = DbLoadSummary(**counts)

    return build_ingest_response(
        result,
        through=through,
        duration_seconds=duration,
        artifacts=artifacts,
        db_load=db_load_summary,
    )


async def run_ingest_with_client(
    client: KalshiClient,
    body: IngestRequest,
) -> IngestResponse:
    """Run ingest with an injected client (for tests)."""
    params = _resolve_request(body)
    through = params.pop("through")
    min_volume = params.pop("min_volume")
    started = time.perf_counter()
    result = await run_etl(
        client,
        min_volume=min_volume,
        through=through,
        **params,
    )
    artifacts: list[str] = []
    if body.persist:
        artifacts = _persist_artifacts(result, through)
    return build_ingest_response(
        result,
        through=through,
        duration_seconds=time.perf_counter() - started,
        artifacts=artifacts,
    )
