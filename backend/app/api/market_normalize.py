"""Collapse multi-outcome event rows into one canonical market per event."""

from __future__ import annotations

from typing import Any


def event_key(row: dict[str, Any]) -> str:
    return row.get("event_ticker") or row["ticker"]


def normalize_market_rows(
    rows: list[dict[str, Any]],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Group markets by event_ticker (fallback: ticker for standalone markets).
    Returns one row per event using the highest-volume outcome as the
    canonical ticker, with volume/OI summed across all siblings.
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(event_key(row), []).append(row)

    normalized: list[dict[str, Any]] = []
    for group in groups.values():
        group.sort(key=lambda r: float(r.get("volume_24h_fp") or 0), reverse=True)
        lead = group[0]
        normalized.append(
            {
                **lead,
                "ticker": lead["ticker"],
                "volume_24h_fp": sum(float(r.get("volume_24h_fp") or 0) for r in group),
                "open_interest_fp": sum(float(r.get("open_interest_fp") or 0) for r in group),
                "outcome_count": len(group),
            }
        )

    normalized.sort(key=lambda r: float(r.get("volume_24h_fp") or 0), reverse=True)
    if limit is not None:
        return normalized[:limit]
    return normalized
