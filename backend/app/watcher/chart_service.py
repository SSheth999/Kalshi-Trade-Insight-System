"""
MarketChartService: on-demand, per-ticker fast poll loop for the market
detail chart. Independent of the top-K WatcherService so opening a chart
never slows down (or is throttled by) the broad watcher basket.

Architecture:
  - One asyncio.Task per subscribed ticker, started lazily on first
    WebSocket subscriber and cancelled once the last one disconnects.
  - Poll interval is intentionally short (default 2s) since at most a
    handful of tickers are ever "focused" (chart open) at once.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import WebSocket

from app.watcher.service import _safe_float

logger = logging.getLogger(__name__)


class MarketChartService:
    def __init__(self, poll_interval_seconds: float = 2.0) -> None:
        self._poll_interval = poll_interval_seconds
        self._tasks: dict[str, asyncio.Task] = {}
        self._clients: dict[str, set[WebSocket]] = {}

    async def connect(self, ticker: str, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.setdefault(ticker, set()).add(ws)
        logger.info(
            "Chart WS client connected for %s (%d total)", ticker, len(self._clients[ticker])
        )
        if ticker not in self._tasks or self._tasks[ticker].done():
            self._tasks[ticker] = asyncio.create_task(
                self._poll_loop(ticker), name=f"chart-poll-{ticker}"
            )

    def disconnect(self, ticker: str, ws: WebSocket) -> None:
        clients = self._clients.get(ticker)
        if clients:
            clients.discard(ws)
        if not clients:
            self._clients.pop(ticker, None)
            task = self._tasks.pop(ticker, None)
            if task and not task.done():
                task.cancel()
            logger.info("Chart WS: no more clients for %s, stopped polling", ticker)

    async def _broadcast(self, ticker: str, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._clients.get(ticker, ())):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ticker, ws)

    async def _poll_loop(self, ticker: str) -> None:
        from app.etl.shared import kalshi_client

        try:
            async with kalshi_client() as client:
                while True:
                    try:
                        resp = await client.get_market(ticker)
                        m = resp.market
                        payload = {
                            "event": "tick",
                            "ticker": ticker,
                            "time": int(time.time()),
                            "price": _safe_float(getattr(m, "last_price_dollars", None)),
                            "yes_bid": _safe_float(getattr(m, "yes_bid_dollars", None)),
                            "yes_ask": _safe_float(getattr(m, "yes_ask_dollars", None)),
                        }
                        await self._broadcast(ticker, payload)
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning("Chart poll failed for %s: %s", ticker, e)

                    await asyncio.sleep(self._poll_interval)
        except asyncio.CancelledError:
            pass

    def status(self) -> dict[str, Any]:
        return {
            "active_tickers": list(self._tasks.keys()),
            "clients_per_ticker": {t: len(c) for t, c in self._clients.items()},
        }


chart_service = MarketChartService()
