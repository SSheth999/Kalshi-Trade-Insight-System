from fastapi import APIRouter

from app.api.ingest_service import run_ingest
from app.api.schemas import IngestRequest, IngestResponse

router = APIRouter()


@router.post("/pipeline/ingest", response_model=IngestResponse)
async def ingest_pipeline(body: IngestRequest | None = None) -> IngestResponse:
    """Run the Kalshi ETL pipeline (phases 1–4) and return a summary."""
    request = body or IngestRequest()
    return await run_ingest(request)
