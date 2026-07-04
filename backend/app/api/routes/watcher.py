from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.watcher.models import WatcherStartRequest, WatcherStatus
from app.watcher.service import watcher

router = APIRouter(prefix="/watcher", tags=["watcher"])


@router.post("/start", response_model=WatcherStatus)
async def start_watcher(body: WatcherStartRequest | None = None) -> WatcherStatus:
    """Start the market watcher poll loop."""
    req = body or WatcherStartRequest()
    watcher.start(poll_interval_seconds=req.poll_interval_seconds, top_k=req.top_k)
    return watcher.status()


@router.post("/stop", response_model=WatcherStatus)
async def stop_watcher() -> WatcherStatus:
    """Stop the market watcher."""
    watcher.stop()
    return watcher.status()


@router.get("/status", response_model=WatcherStatus)
async def get_watcher_status() -> WatcherStatus:
    return watcher.status()


@router.websocket("/ws")
async def market_feed(ws: WebSocket) -> None:
    """
    WebSocket endpoint. Connect to receive live market snapshots.

    Message shape:
      {
        "event": "snapshot",
        "poll_count": 12,
        "tickers": [
          {
            "ticker": "KXMLBGAME-24-...",
            "series_ticker": "KXMLBGAME",
            "last_price_dollars": 0.61,
            "yes_bid_dollars": 0.60,
            "yes_ask_dollars": 0.62,
            "volume_24h_fp": 42500.0,
            "open_interest_fp": 18000.0,
            "price_delta": 0.01        // null on first poll
          },
          ...
        ]
      }
    """
    await watcher.connect(ws)
    try:
        while True:
            # Keep the connection alive; we don't expect messages from the client.
            data = await ws.receive_text()
            if data.strip().lower() in ("ping", "pong"):
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        watcher.disconnect(ws)