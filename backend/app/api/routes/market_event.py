from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.schemas import EventMarketsResponse, EventOutcomeRow
from app.db.session import get_session

router = APIRouter(tags=["market-event"])


def _outcome_label(market_ticker: str, event_ticker: str | None) -> str:
    if event_ticker and market_ticker.startswith(f"{event_ticker}-"):
        return market_ticker[len(event_ticker) + 1 :]
    parts = market_ticker.rsplit("-", 1)
    return parts[-1] if len(parts) > 1 else market_ticker


@router.get("/markets/{ticker}/event", response_model=EventMarketsResponse)
async def get_market_event(ticker: str) -> EventMarketsResponse:
    """
    Resolve all sibling outcome markets for the event containing `ticker`.
    Falls back to a single-outcome response when event_ticker is missing.
    """
    with get_session() as session:
        anchor = session.execute(
            text(
                """
                select ticker, series_ticker, event_ticker, title, status,
                       yes_bid_dollars, yes_ask_dollars, last_price_dollars, previous_price_dollars,
                       volume_24h_fp, open_interest_fp, close_time
                from markets
                where ticker = :ticker
                """
            ),
            {"ticker": ticker},
        ).fetchone()

        if not anchor:
            raise HTTPException(status_code=404, detail=f"Market '{ticker}' not found")

        anchor_row = dict(anchor._mapping)
        event_ticker = anchor_row.get("event_ticker")

        if event_ticker:
            rows = session.execute(
                text(
                    """
                    select ticker, series_ticker, event_ticker, title, status,
                           yes_bid_dollars, yes_ask_dollars, last_price_dollars, previous_price_dollars,
                           volume_24h_fp, open_interest_fp, close_time
                    from markets
                    where event_ticker = :event_ticker
                    order by volume_24h_fp desc nulls last, ticker
                    """
                ),
                {"event_ticker": event_ticker},
            ).fetchall()
        else:
            rows = [anchor]

    outcomes = [
        EventOutcomeRow(
            **dict(r._mapping),
            outcome_label=_outcome_label(r.ticker, event_ticker),
        )
        for r in rows
    ]

    title = anchor_row.get("title")
    series_ticker = anchor_row.get("series_ticker")

    return EventMarketsResponse(
        event_ticker=event_ticker or ticker,
        title=title,
        series_ticker=series_ticker,
        outcome_count=len(outcomes),
        outcomes=outcomes,
    )
