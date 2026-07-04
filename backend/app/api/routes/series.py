from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.schemas import MarketRow, SeriesMarketsResponse
from app.db.session import get_session

router = APIRouter(prefix="/series", tags=["series"])


@router.get("/{ticker}/markets", response_model=SeriesMarketsResponse)
async def get_series_markets(ticker: str, limit: int = 50) -> SeriesMarketsResponse:
    """Drill-down: list markets for a series, most-traded first."""
    with get_session() as session:
        rows = session.execute(
            text(
                """
                select ticker, event_ticker, title, status,
                       yes_bid_dollars, yes_ask_dollars, last_price_dollars, previous_price_dollars,
                       volume_24h_fp, open_interest_fp, close_time
                from markets
                where series_ticker = :ticker
                order by volume_24h_fp desc nulls last
                limit :limit
                """
            ),
            {"ticker": ticker, "limit": limit},
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No markets found for series '{ticker}'")

    markets = [MarketRow(**dict(r._mapping)) for r in rows]
    return SeriesMarketsResponse(
        series_ticker=ticker,
        market_count=len(markets),
        markets=markets,
    )
