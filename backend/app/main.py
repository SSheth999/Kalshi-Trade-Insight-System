import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.market_chart import router as market_chart_router
from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.series import router as series_router
from app.api.routes.watcher import router as watcher_router

logger = logging.getLogger(__name__)

# Auto-run configuration: through=3 (discover + score + collect, no candlesticks)
# keeps startup fast (~15-20s) while still populating series/markets tables
# for the dashboard and the watcher to read from.
AUTO_INGEST_THROUGH = 3
AUTO_INGEST_TOP_K = 6
AUTO_WATCHER_POLL_SECONDS = 20.0
AUTO_WATCHER_TOP_K = 15


async def _run_startup_pipeline() -> None:
    from app.api.ingest_service import run_ingest
    from app.api.schemas import IngestRequest
    from app.state import state
    from app.watcher.service import watcher

    state.ingest_status = "running"
    state.ingest_started_at = datetime.now(timezone.utc)
    try:
        request = IngestRequest(
            through=AUTO_INGEST_THROUGH,
            top_k=AUTO_INGEST_TOP_K,
            persist_db=True,
        )
        result = await run_ingest(request)
        state.latest_ingest = result
        state.ingest_status = "ready"
        state.ingest_completed_at = datetime.now(timezone.utc)
        logger.info("Startup ingestion complete: through=%d", result.through)

        watcher.start(
            poll_interval_seconds=AUTO_WATCHER_POLL_SECONDS,
            top_k=AUTO_WATCHER_TOP_K,
        )
        logger.info("Watcher auto-started after ingestion")
    except Exception as e:
        state.ingest_status = "error"
        state.ingest_error = str(e)
        state.ingest_completed_at = datetime.now(timezone.utc)
        logger.error("Startup ingestion failed: %s", e, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    from app.watcher.service import watcher

    startup_task = asyncio.create_task(_run_startup_pipeline())
    try:
        yield
    finally:
        watcher.stop()
        if not startup_task.done():
            startup_task.cancel()


app = FastAPI(
    title="Kalshi Trade Insight System",
    description="Kalshi ingestion and trade insight API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pipeline_router, prefix="/api/v1", tags=["pipeline"])
app.include_router(watcher_router, prefix="/api/v1", tags=["watcher"])
app.include_router(series_router, prefix="/api/v1", tags=["series"])
app.include_router(market_chart_router, prefix="/api/v1", tags=["market-chart"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
