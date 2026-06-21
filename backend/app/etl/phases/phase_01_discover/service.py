from kalshi_python_async import KalshiClient

from app.etl.phases.phase_01_discover.models import SeriesCandidate, SeriesUniverseResult


def _parse_volume(volume_fp: str | None) -> float:
    if not volume_fp:
        return 0.0
    return float(volume_fp)


def _to_candidate(series) -> SeriesCandidate:
    return SeriesCandidate(
        ticker=series.ticker,
        title=series.title,
        category=series.category,
        frequency=series.frequency,
        tags=series.tags or [],
        volume=_parse_volume(series.volume_fp),
        last_updated_ts=series.last_updated_ts,
    )


async def discover_series(
    client: KalshiClient,
    *,
    min_volume: float = 1000,
    category: str | None = None,
) -> SeriesUniverseResult:
    """Fetch series universe filtered by lifetime volume >= min_volume."""
    response = await client.get_series_list(
        include_volume=True,
        category=category,
    )

    all_series = response.series
    candidates: list[SeriesCandidate] = []

    for series in all_series:
        volume = _parse_volume(series.volume_fp)
        if volume >= min_volume:
            candidates.append(_to_candidate(series))

    candidates.sort(key=lambda s: s.volume, reverse=True)

    return SeriesUniverseResult(
        min_volume=min_volume,
        total_series_fetched=len(all_series),
        series_passing_volume_filter=len(candidates),
        series=candidates,
    )
