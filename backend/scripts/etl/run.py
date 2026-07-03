#!/usr/bin/env python3
"""Run Kalshi ETL phases."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.etl.config import settings
from app.etl.phases.phase_01_discover import SeriesUniverseResult
from app.etl.run import run_etl
from app.etl.shared import kalshi_client, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Kalshi ETL pipeline phases")
    parser.add_argument(
        "--through",
        type=int,
        choices=[1, 2, 3, 4],
        default=2,
        help="Run through phase N (1=discover, 2=score, 3=collect, 4=history)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="Phase 1 JSON to skip discover (requires --through >= 2)",
    )
    parser.add_argument(
        "--min-volume",
        type=float,
        default=settings.min_series_volume,
        help=f"Min series volume for phase 1 (default: {settings.min_series_volume})",
    )
    parser.add_argument(
        "--max-series-to-score",
        type=int,
        default=settings.max_series_to_score,
        help=f"Phase 2: score top N by volume (default: {settings.max_series_to_score})",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=settings.top_volatile_series,
        help=f"Phase 2: return top K volatile series (default: {settings.top_volatile_series})",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=settings.score_concurrency,
        help=f"Phase 2: parallel requests (default: {settings.score_concurrency})",
    )
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=settings.lookback_days,
        help=f"Phase 4: days of candlestick history (default: {settings.lookback_days})",
    )
    parser.add_argument(
        "--period-interval",
        type=int,
        choices=[1, 60, 1440],
        default=settings.period_interval,
        help=f"Phase 4: candlestick interval in minutes (default: {settings.period_interval})",
    )
    parser.add_argument(
        "--max-markets-per-series",
        type=int,
        default=settings.max_markets_per_series,
        help=(
            f"Phase 4: max markets per series by 24h volume "
            f"(default: {settings.max_markets_per_series})"
        ),
    )
    parser.add_argument(
        "--candlestick-concurrency",
        type=int,
        default=settings.candlestick_concurrency,
        help=f"Phase 4: parallel batch requests (default: {settings.candlestick_concurrency})",
    )
    parser.add_argument(
        "--universe-output",
        type=Path,
        default=Path(settings.data_dir) / "series_universe.json",
        help="Phase 1 output path",
    )
    parser.add_argument(
        "--rankings-output",
        type=Path,
        default=Path(settings.data_dir) / "series_rankings.json",
        help="Phase 2 output path",
    )
    parser.add_argument(
        "--history-output",
        type=Path,
        default=Path(settings.data_dir) / "candlestick_history.json",
        help="Phase 4 output path",
    )
    return parser.parse_args()


def _load_universe(path: Path) -> SeriesUniverseResult:
    data = json.loads(path.read_text(encoding="utf-8"))
    return SeriesUniverseResult.model_validate(data)


async def main() -> None:
    args = parse_args()

    if args.input and args.through < 2:
        raise SystemExit("--input requires --through >= 2")

    async with kalshi_client() as client:
        if args.input:
            universe = _load_universe(args.input)
            print(f"Loaded phase 1 output: {len(universe.series)} series from {args.input}")
            result = await run_etl(
                client,
                min_volume=universe.min_volume,
                through=args.through,
                top_k=args.top_k,
                max_series_to_score=args.max_series_to_score,
                concurrency=args.concurrency,
                universe=universe,
                lookback_days=args.lookback_days,
                period_interval=args.period_interval,
                max_markets_per_series=args.max_markets_per_series,
                candlestick_concurrency=args.candlestick_concurrency,
            )
        else:
            result = await run_etl(
                client,
                min_volume=args.min_volume,
                through=args.through,
                top_k=args.top_k,
                max_series_to_score=args.max_series_to_score,
                concurrency=args.concurrency,
                lookback_days=args.lookback_days,
                period_interval=args.period_interval,
                max_markets_per_series=args.max_markets_per_series,
                candlestick_concurrency=args.candlestick_concurrency,
            )

    if args.input is None or args.through >= 1:
        save_json(args.universe_output, result.universe)
        print(
            f"Phase 1: {result.universe.series_passing_volume_filter} series "
            f"with volume >= {result.universe.min_volume} → {args.universe_output.resolve()}"
        )

    if result.rankings is not None:
        save_json(args.rankings_output, result.rankings)
        print(
            f"Phase 2: scored {result.rankings.series_scored}, "
            f"skipped {result.rankings.series_skipped_no_open_markets}, "
            f"cached {len(result.markets_store)} series in memory → "
            f"{args.rankings_output.resolve()}"
        )
        for series in result.rankings.ranked_series:
            m = series.metrics
            print(
                f"  {series.ticker:20} score={series.score:>8.4f}  "
                f"max_move={m.max_1d_move:.4f} spread={m.avg_spread:.4f}  "
                f"vol24={m.total_vol24:,.0f} markets={m.open_market_count}  "
                f"{series.title}"
            )

    if result.collected is not None:
        total_markets = sum(s.market_count for s in result.collected.series)
        print(
            f"\nPhase 3: collected {total_markets} markets across "
            f"{len(result.collected.series)} volatile series (in-memory store only)"
        )
        for series in result.collected.series:
            print(f"  {series.series_ticker:20} {series.market_count} markets")

    if result.history is not None:
        save_json(args.history_output, result.history)
        total_candles = sum(
            m.candlestick_count
            for s in result.history.series
            for m in s.markets
        )
        print(
            f"\nPhase 4: fetched {result.history.markets_fetched} markets, "
            f"{total_candles} candlesticks, "
            f"{len(result.history.markets_failed)} failed → "
            f"{args.history_output.resolve()}"
        )
        for series in result.history.series:
            series_candles = sum(m.candlestick_count for m in series.markets)
            print(
                f"  {series.series_ticker:20} "
                f"{len(series.markets)} markets, {series_candles} candlesticks"
            )


if __name__ == "__main__":
    asyncio.run(main())
