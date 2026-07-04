import logging
import time

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.etl.phases.phase_04_history.routing import iter_time_windows
from app.etl.shared import kalshi_client
from app.etl.shared.retry import with_retry
from app.watcher.chart_models import CandlestickPoint, CandlesticksResponse
from app.watcher.chart_service import chart_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["market-chart"])


def _to_float(val: str | None) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@router.get("/markets/{ticker}/candlesticks", response_model=CandlesticksResponse)
async def get_market_candlesticks(
    ticker: str,
    period_interval: int = 1,
    lookback_minutes: int = 1440,
) -> CandlesticksResponse:
    """
    Historical backbone for the market chart, fetched live from Kalshi
    (no dependency on the batch ETL / candlesticks table — works for any
    market ticker, not just ones already ingested through Phase 4).
    """
    if period_interval not in (1, 60, 1440):
        raise HTTPException(status_code=400, detail="period_interval must be 1, 60, or 1440")

    end_ts = int(time.time())
    start_ts = end_ts - lookback_minutes * 60

    points: list[CandlestickPoint] = []
    try:
        async with kalshi_client() as client:
            for window_start, window_end in iter_time_windows(start_ts, end_ts, period_interval):
                response = await with_retry(
                    lambda ws=window_start, we=window_end: client.batch_get_market_candlesticks(
                        market_tickers=ticker,
                        start_ts=ws,
                        end_ts=we,
                        period_interval=period_interval,
                        include_latest_before_start=False,
                    )
                )
                for market_data in response.markets:
                    for c in market_data.candlesticks:
                        price = c.price
                        points.append(
                            CandlestickPoint(
                                time=c.end_period_ts,
                                open=_to_float(price.open_dollars if price else None),
                                high=_to_float(price.high_dollars if price else None),
                                low=_to_float(price.low_dollars if price else None),
                                close=_to_float(price.close_dollars if price else None),
                                volume=_to_float(c.volume_fp),
                            )
                        )
    except Exception as e:
        logger.error("Candlestick fetch failed for %s: %s", ticker, e, exc_info=True)
        raise HTTPException(status_code=502, detail=f"Kalshi candlestick fetch failed: {e}") from e

    points.sort(key=lambda p: p.time)
    return CandlesticksResponse(ticker=ticker, period_interval=period_interval, candles=points)


@router.websocket("/markets/{ticker}/ws")
async def market_chart_feed(ws: WebSocket, ticker: str) -> None:
    """
    Dedicated live feed for a single market, polled fast (~2s) while at
    least one client is connected. Independent of the top-K watcher.

    Message shape:
      { "event": "tick", "ticker": "...", "time": 1735900000,
        "price": 0.61, "yes_bid": 0.60, "yes_ask": 0.62 }
    """
    await chart_service.connect(ticker, ws)
    try:
        while True:
            data = await ws.receive_text()
            if data.strip().lower() in ("ping", "pong"):
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        chart_service.disconnect(ticker, ws)
