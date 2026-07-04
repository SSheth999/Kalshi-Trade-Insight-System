from fastapi import FastAPI

from app.api.routes.pipeline import router as pipeline_router
from app.api.routes.watcher import router as watcher_router

app = FastAPI(
    title="Kalshi Trade Insight System",
    description="Kalshi ingestion and trade insight API",
    version="0.1.0",
)

app.include_router(pipeline_router, prefix="/api/v1", tags=["pipeline"])
app.include_router(watcher_router, prefix="/api/v1", tags=["watcher"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
