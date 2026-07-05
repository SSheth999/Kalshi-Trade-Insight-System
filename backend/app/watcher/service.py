"""
WatcherService: polls top-K Kalshi market tickers on a fixed interval
and broadcasts price/spread snapshots to all connected WebSocket clients.

Architecture:
  - A single background asyncio.Task runs the poll loop.
  - Connected WebSockets are stored in a set; the loop broadcasts to all.
  - Price state is kept in-memory to compute deltas between polls.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from app.watcher.models import MarketTick, WatcherSnapshot, WatcherStatus

logger = logging.getLogger(__name__)


class WatcherService:
    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._task: asyncio.Task | None = None
        self._poll_interval: float = 30.0
        self._top_k: int = 20
        self._poll_count: int = 0
        # ticker → last_price_dollars for delta computation
        self._prev_prices: dict[str, float | None] = {}

    # ── state ──────────────────────────────────────────────────────────────────

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> WatcherStatus:
        return WatcherStatus(
            running=self.running,
            poll_interval_seconds=self._poll_interval if self.running else None,
            top_k=self._top_k if self.running else None,
            poll_count=self._poll_count,
            connected_clients=len(self._clients),
        )

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def start(self, poll_interval_seconds: float = 30.0, top_k: int = 20) -> None:
        if self.running:
            logger.info("Watcher already running; ignoring start()")
            return
        self._poll_interval = poll_interval_seconds
        self._top_k = top_k
        self._poll_count = 0
        self._prev_prices.clear()
        self._task = asyncio.create_task(self._poll_loop(), name="watcher-poll-loop")
        logger.info("WatcherService started: interval=%.1fs top_k=%d", poll_interval_seconds, top_k)

    def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("WatcherService stopped")
        self._task = None

    # ── WebSocket client management ────────────────────────────────────────────

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._clients.add(ws)
        logger.info("WS client connected (%d total)", len(self._clients))

    def disconnect(self, ws: WebSocket) -> None:
        self._clients.discard(ws)
        logger.info("WS client disconnected (%d remaining)", len(self._clients))

    # ── broadcast ──────────────────────────────────────────────────────────────

    async def _broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._clients):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)

    # ── polling ────────────────────────────────────────────────────────────────

    async def _fetch_top_k_tickers(self) -> list[dict[str, Any]]:
        """
        Pull the most recent top-K market tickers from the DB (by series rank),
        then hit the Kalshi API for live quotes.

        Falls back to DB snapshot values if the live fetch fails.
        """
        from sqlalchemy import text

        from app.db.session import get_session
        from app.etl.shared import kalshi_client

        # Step 1: get top-K market tickers from the latest rankings
        with get_session() as session:
            rows = session.execute(
                text(
                    """
                    with ranked_outcomes as (
                        select m.ticker, m.series_ticker,
                               m.last_price_dollars, m.yes_bid_dollars, m.yes_ask_dollars,
                               m.volume_24h_fp, m.open_interest_fp,
                               sr.rank as series_rank,
                               row_number() over (
                                   partition by coalesce(m.event_ticker, m.ticker)
                                   order by m.volume_24h_fp desc nulls last
                               ) as outcome_rn
                        from markets m
                        join series_rankings sr on sr.series_ticker = m.series_ticker
                        where sr.run_id = (
                            select id from ingestion_runs
                            order by completed_at desc nulls last limit 1
                        )
                        and m.status in ('active', 'open')
                    )
                    select ticker, series_ticker,
                           last_price_dollars, yes_bid_dollars, yes_ask_dollars,
                           volume_24h_fp, open_interest_fp
                    from ranked_outcomes
                    where outcome_rn = 1
                    order by series_rank, volume_24h_fp desc nulls last
                    limit :top_k
                    """
                ),
                {"top_k": self._top_k},
            ).fetchall()

        if not rows:
            return []

        db_tickers = [dict(r._mapping) for r in rows]

        # Step 2: attempt live refresh from Kalshi for these specific tickers
        ticker_list = [r["ticker"] for r in db_tickers]
        try:
            async with kalshi_client() as client:
                live_map: dict[str, Any] = {}
                # Kalshi get_market supports single tickers; batch with semaphore
                sem = asyncio.Semaphore(10)

                async def _fetch_one(t: str) -> None:
                    async with sem:
                        try:
                            resp = await client.get_market(t)
                            m = resp.market
                            live_map[t] = {
                                "ticker": t,
                                "last_price_dollars": _safe_float(getattr(m, "last_price_dollars", None)),
                                "yes_bid_dollars": _safe_float(getattr(m, "yes_bid_dollars", None)),
                                "yes_ask_dollars": _safe_float(getattr(m, "yes_ask_dollars", None)),
                                "volume_24h_fp": _safe_float(getattr(m, "volume_24h_fp", None)),
                                "open_interest_fp": _safe_float(getattr(m, "open_interest_fp", None)),
                            }
                        except Exception as e:
                            logger.debug("Live fetch failed for %s: %s", t, e)

                await asyncio.gather(*[_fetch_one(t) for t in ticker_list])

            # Merge: prefer live data, fall back to DB row (series_ticker always comes from DB)
            merged: list[dict[str, Any]] = []
            for row in db_tickers:
                t = row["ticker"]
                if t in live_map:
                    merged.append({**live_map[t], "series_ticker": row["series_ticker"]})
                else:
                    row_copy = dict(row)
                    row_copy["last_price_dollars"] = _safe_float(row_copy.get("last_price_dollars"))
                    row_copy["yes_bid_dollars"] = _safe_float(row_copy.get("yes_bid_dollars"))
                    row_copy["yes_ask_dollars"] = _safe_float(row_copy.get("yes_ask_dollars"))
                    row_copy["volume_24h_fp"] = _safe_float(row_copy.get("volume_24h_fp"))
                    row_copy["open_interest_fp"] = _safe_float(row_copy.get("open_interest_fp"))
                    merged.append(row_copy)
            return merged

        except Exception as e:
            logger.warning("Live refresh failed, using DB snapshot: %s", e)
            return [
                {
                    **dict(r),
                    "last_price_dollars": _safe_float(r["last_price_dollars"]),
                    "yes_bid_dollars": _safe_float(r["yes_bid_dollars"]),
                    "yes_ask_dollars": _safe_float(r["yes_ask_dollars"]),
                    "volume_24h_fp": _safe_float(r["volume_24h_fp"]),
                    "open_interest_fp": _safe_float(r["open_interest_fp"]),
                }
                for r in db_tickers
            ]

    async def _poll_loop(self) -> None:
        while True:
            try:
                raw = await self._fetch_top_k_tickers()
                self._poll_count += 1

                ticks: list[MarketTick] = []
                for r in raw:
                    ticker = r["ticker"]
                    cur_price = r.get("last_price_dollars")
                    prev_price = self._prev_prices.get(ticker)
                    delta = (cur_price - prev_price) if (cur_price is not None and prev_price is not None) else None
                    self._prev_prices[ticker] = cur_price
                    ticks.append(
                        MarketTick(
                            ticker=ticker,
                            series_ticker=r.get("series_ticker") or "",
                            last_price_dollars=cur_price,
                            yes_bid_dollars=r.get("yes_bid_dollars"),
                            yes_ask_dollars=r.get("yes_ask_dollars"),
                            volume_24h_fp=r.get("volume_24h_fp"),
                            open_interest_fp=r.get("open_interest_fp"),
                            price_delta=delta,
                        )
                    )

                snapshot = WatcherSnapshot(poll_count=self._poll_count, tickers=ticks)
                await self._broadcast(snapshot.model_dump())
                logger.info("Watcher poll #%d: %d tickers → %d clients", self._poll_count, len(ticks), len(self._clients))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Poll loop error: %s", e, exc_info=True)

            await asyncio.sleep(self._poll_interval)


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# Singleton used by routes
watcher = WatcherService()
