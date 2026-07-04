from fastapi import APIRouter

from app.api.ingest_service import run_ingest
from app.api.schemas import IngestRequest, IngestResponse, LatestIngestResponse
from app.state import state

router = APIRouter()


@router.post("/pipeline/ingest", response_model=IngestResponse)
async def ingest_pipeline(body: IngestRequest | None = None) -> IngestResponse:
    """Run the Kalshi ETL pipeline (phases 1–4) and return a summary."""
    request = body or IngestRequest()
    state.ingest_status = "running"
    try:
        result = await run_ingest(request)
    except Exception as e:
        state.ingest_status = "error"
        state.ingest_error = str(e)
        raise
    state.latest_ingest = result
    state.ingest_status = "ready"
    return result


@router.get("/pipeline/latest", response_model=LatestIngestResponse)
async def get_latest_ingest() -> LatestIngestResponse:
    """Return the most recent ingestion result (auto-run on startup, or last manual run)."""
    return LatestIngestResponse(
        status=state.ingest_status,
        result=state.latest_ingest,
        error=state.ingest_error,
        started_at=state.ingest_started_at,
        completed_at=state.ingest_completed_at,
    )
