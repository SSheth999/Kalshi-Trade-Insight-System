from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.market_normalize import normalize_market_rows
from app.api.schemas import MarketRow, SeriesMarketsResponse
from app.db.session import get_session

router = APIRouter(prefix="/series", tags=["series"])

# Fetch extra rows before normalization so limit still fills after deduping siblings.
_FETCH_MULTIPLIER = 4


@router.get("/{ticker}/markets", response_model=SeriesMarketsResponse)
async def get_series_markets(ticker: str, limit: int = 50) -> SeriesMarketsResponse:
    """Drill-down: one row per event (deduped siblings), most-traded first."""
    fetch_limit = min(limit * _FETCH_MULTIPLIER, 500)

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
                limit :fetch_limit
                """
            ),
            {"ticker": ticker, "fetch_limit": fetch_limit},
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"No markets found for series '{ticker}'")

    raw = [dict(r._mapping) for r in rows]
    normalized = normalize_market_rows(raw, limit=limit)
    markets = [MarketRow(**row) for row in normalized]

    return SeriesMarketsResponse(
        series_ticker=ticker,
        market_count=len(markets),
        markets=markets,
    )
