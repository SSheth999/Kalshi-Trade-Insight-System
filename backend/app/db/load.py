"""Upsert PipelineResult into Postgres/Supabase tables."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.etl.run import PipelineResult


# ─── helpers ──────────────────────────────────────────────────────────────────

def _parse_num(val: str | None) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _batch(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _pg_text_array(values: list[str]) -> str:
    """Convert a Python list of strings to a Postgres text[] literal."""
    escaped = [v.replace('"', '\\"') for v in values]
    return "{" + ",".join(f'"{v}"' for v in escaped) + "}"


# ─── per-table upserts ────────────────────────────────────────────────────────

def _upsert_series(session: Session, result: PipelineResult) -> None:
    """Upsert ranked series (top-K) into the series dimension table."""
    if result.rankings is None:
        return

    rows: list[dict[str, Any]] = []
    for s in result.rankings.ranked_series:
        rows.append(
            {
                "ticker": s.ticker,
                "title": s.title,
                "category": s.category,
                "frequency": s.frequency,
                "tags": _pg_text_array(s.tags),
                "lifetime_volume": s.volume,
                "last_updated_ts": None,
                "updated_at": datetime.now(timezone.utc),
            }
        )

    if not rows:
        return

    session.execute(
        text(
            """
            insert into series (ticker, title, category, frequency, tags, lifetime_volume,
                                last_updated_ts, updated_at)
            values (:ticker, :title, :category, :frequency, CAST(:tags AS text[]), :lifetime_volume,
                    :last_updated_ts, :updated_at)
            on conflict (ticker) do update set
                title            = excluded.title,
                category         = excluded.category,
                frequency        = excluded.frequency,
                tags             = excluded.tags,
                lifetime_volume  = excluded.lifetime_volume,
                updated_at       = excluded.updated_at
            """
        ),
        rows,
    )


def _upsert_markets(session: Session, result: PipelineResult) -> int:
    """Upsert market snapshots for top-K series. Returns count upserted."""
    if result.collected is None:
        return 0

    rows: list[dict[str, Any]] = []
    for series in result.collected.series:
        for m in series.markets:
            rows.append(
                {
                    "ticker": m.ticker,
                    "series_ticker": series.series_ticker,
                    "event_ticker": m.event_ticker,
                    "title": m.title,
                    "status": m.status,
                    "yes_bid_dollars": _parse_num(m.yes_bid_dollars),
                    "yes_ask_dollars": _parse_num(m.yes_ask_dollars),
                    "last_price_dollars": _parse_num(m.last_price_dollars),
                    "previous_price_dollars": _parse_num(m.previous_price_dollars),
                    "volume_24h_fp": _parse_num(m.volume_24h_fp),
                    "open_interest_fp": _parse_num(m.open_interest_fp),
                    "close_time": m.close_time,
                    "rules_primary": m.rules_primary,
                    "rules_secondary": m.rules_secondary,
                    "updated_at": datetime.now(timezone.utc),
                }
            )

    if not rows:
        return 0

    for chunk in _batch(rows, 500):
        session.execute(
            text(
                """
                insert into markets (
                    ticker, series_ticker, event_ticker, title, status,
                    yes_bid_dollars, yes_ask_dollars, last_price_dollars, previous_price_dollars,
                    volume_24h_fp, open_interest_fp, close_time,
                    rules_primary, rules_secondary, updated_at
                )
                values (
                    :ticker, :series_ticker, :event_ticker, :title, :status,
                    :yes_bid_dollars, :yes_ask_dollars, :last_price_dollars, :previous_price_dollars,
                    :volume_24h_fp, :open_interest_fp, :close_time,
                    :rules_primary, :rules_secondary, :updated_at
                )
                on conflict (ticker) do update set
                    event_ticker            = excluded.event_ticker,
                    title                   = excluded.title,
                    status                  = excluded.status,
                    yes_bid_dollars         = excluded.yes_bid_dollars,
                    yes_ask_dollars         = excluded.yes_ask_dollars,
                    last_price_dollars      = excluded.last_price_dollars,
                    previous_price_dollars  = excluded.previous_price_dollars,
                    volume_24h_fp           = excluded.volume_24h_fp,
                    open_interest_fp        = excluded.open_interest_fp,
                    close_time              = excluded.close_time,
                    rules_primary           = excluded.rules_primary,
                    rules_secondary         = excluded.rules_secondary,
                    updated_at              = excluded.updated_at
                """
            ),
            chunk,
        )

    return len(rows)


def _insert_rankings(
    session: Session, result: PipelineResult, run_id: str
) -> int:
    """Insert per-run series rankings. Returns count inserted."""
    if result.rankings is None:
        return 0

    rows: list[dict[str, Any]] = []
    for rank, s in enumerate(result.rankings.ranked_series, start=1):
        rows.append(
            {
                "run_id": run_id,
                "series_ticker": s.ticker,
                "rank": rank,
                "score": s.score,
                "avg_spread": s.metrics.avg_spread,
                "max_1d_move": s.metrics.max_1d_move,
                "mean_1d_move": s.metrics.mean_1d_move,
                "total_vol24": s.metrics.total_vol24,
                "open_market_count": s.metrics.open_market_count,
            }
        )

    if not rows:
        return 0

    session.execute(
        text(
            """
            insert into series_rankings (
                run_id, series_ticker, rank, score,
                avg_spread, max_1d_move, mean_1d_move, total_vol24, open_market_count
            )
            values (
                :run_id, :series_ticker, :rank, :score,
                :avg_spread, :max_1d_move, :mean_1d_move, :total_vol24, :open_market_count
            )
            on conflict (run_id, series_ticker) do nothing
            """
        ),
        rows,
    )
    return len(rows)


def _upsert_candlesticks(session: Session, result: PipelineResult) -> int:
    """Upsert candlesticks. Returns count upserted."""
    if result.history is None:
        return 0

    rows: list[dict[str, Any]] = []
    for series in result.history.series:
        for market in series.markets:
            for c in market.candlesticks:
                rows.append(
                    {
                        "market_ticker": market.ticker,
                        "end_period_ts": c.end_period_ts,
                        "period_interval": result.history.period_interval,
                        "open_dollars": _parse_num(c.open_dollars),
                        "high_dollars": _parse_num(c.high_dollars),
                        "low_dollars": _parse_num(c.low_dollars),
                        "close_dollars": _parse_num(c.close_dollars),
                        "volume_fp": _parse_num(c.volume_fp),
                        "open_interest_fp": _parse_num(c.open_interest_fp),
                        "updated_at": datetime.now(timezone.utc),
                    }
                )

    if not rows:
        return 0

    for chunk in _batch(rows, 500):
        session.execute(
            text(
                """
                insert into candlesticks (
                    market_ticker, end_period_ts, period_interval,
                    open_dollars, high_dollars, low_dollars, close_dollars,
                    volume_fp, open_interest_fp, updated_at
                )
                values (
                    :market_ticker, :end_period_ts, :period_interval,
                    :open_dollars, :high_dollars, :low_dollars, :close_dollars,
                    :volume_fp, :open_interest_fp, :updated_at
                )
                on conflict (market_ticker, end_period_ts, period_interval) do update set
                    open_dollars     = excluded.open_dollars,
                    high_dollars     = excluded.high_dollars,
                    low_dollars      = excluded.low_dollars,
                    close_dollars    = excluded.close_dollars,
                    volume_fp        = excluded.volume_fp,
                    open_interest_fp = excluded.open_interest_fp,
                    updated_at       = excluded.updated_at
                """
            ),
            chunk,
        )

    return len(rows)


# ─── main entry point ─────────────────────────────────────────────────────────

def load_pipeline_result(
    result: PipelineResult,
    *,
    through: int,
    duration_seconds: float,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Upsert all pipeline data into Postgres.
    Returns a counts summary and the ingestion run_id.
    """
    from app.db.session import get_session

    run_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    import json as _json

    with get_session() as session:
        # 1. open ingestion run
        session.execute(
            text(
                """
                insert into ingestion_runs (id, started_at, through, params)
                values (:id, :started_at, :through, CAST(:params AS jsonb))
                """
            ),
            {
                "id": run_id,
                "started_at": now,
                "through": through,
                "params": _json.dumps(params or {}),
            },
        )

        # 2. series upsert
        _upsert_series(session, result)

        # 3. markets upsert
        markets_count = _upsert_markets(session, result)

        # 4. per-run rankings
        rankings_count = _insert_rankings(session, result, run_id)

        # 5. candlesticks upsert
        candles_count = _upsert_candlesticks(session, result)

        # 6. close ingestion run
        session.execute(
            text(
                """
                update ingestion_runs
                set completed_at = :completed_at, duration_seconds = :duration, status = 'completed'
                where id = :id
                """
            ),
            {"completed_at": datetime.now(timezone.utc), "duration": duration_seconds, "id": run_id},
        )

        session.commit()

    return {
        "run_id": run_id,
        "series_upserted": len(result.rankings.ranked_series) if result.rankings else 0,
        "markets_upserted": markets_count,
        "rankings_inserted": rankings_count,
        "candlesticks_upserted": candles_count,
    }
