import importlib
from datetime import datetime, timezone

import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.etl.phases.phase_01_discover import SeriesCandidate, discover_series
from app.etl.phases.phase_02_score import score_series as run_score_series
from app.etl.phases.phase_02_score.models import SeriesVolatilityMetrics
from app.etl.phases.phase_02_score.volatility import (
    aggregate_market_signals,
    composite_score,
    to_ranked,
)
from app.etl.phases.phase_03_collect import collect_markets
from app.etl.phases.phase_04_history.routing import (
    candles_per_market,
    iter_time_windows,
    max_tickers_per_batch,
)
from app.etl.shared.markets_store import MarketsStore


def _market(
    *,
    ticker: str = "MKT-1",
    bid: str = "0.50",
    ask: str = "0.55",
    last: str = "0.52",
    previous: str = "0.40",
    vol24: str = "1000.00",
):
    return SimpleNamespace(
        ticker=ticker,
        event_ticker="EVT-1",
        title="Test Market",
        status="open",
        yes_bid_dollars=bid,
        yes_ask_dollars=ask,
        last_price_dollars=last,
        previous_price_dollars=previous,
        volume_24h_fp=vol24,
        open_interest_fp="500.00",
        close_time=datetime(2026, 6, 21, tzinfo=timezone.utc),
    )


class TestPhase02Volatility:
    def test_aggregate_market_signals(self):
        markets = [
            _market(bid="0.50", ask="0.60", last="0.55", previous="0.45", vol24="100.00"),
            _market(bid="0.30", ask="0.35", last="0.80", previous="0.20", vol24="200.00"),
        ]
        metrics = aggregate_market_signals(markets)

        assert metrics is not None
        assert metrics.avg_spread == pytest.approx(0.075)
        assert metrics.max_1d_move == pytest.approx(0.60)
        assert metrics.mean_1d_move == pytest.approx(0.35)
        assert metrics.total_vol24 == pytest.approx(300.0)
        assert metrics.open_market_count == 2

    def test_aggregate_empty_markets_returns_none(self):
        assert aggregate_market_signals([]) is None

    def test_composite_score(self):
        metrics = SeriesVolatilityMetrics(
            avg_spread=0.05,
            max_1d_move=0.20,
            mean_1d_move=0.10,
            total_vol24=1000.0,
            open_market_count=3,
        )
        score = composite_score(metrics)
        assert score == pytest.approx(0.4 * 0.20 + 0.3 * 0.05 + 0.3 * __import__("math").log1p(1000))

    def test_to_ranked_carries_candidate_fields(self):
        candidate = SeriesCandidate(
            ticker="KXTEST",
            title="Test Series",
            category="Crypto",
            frequency="daily",
            tags=["test"],
            volume=5000.0,
        )
        metrics = SeriesVolatilityMetrics(
            avg_spread=0.01,
            max_1d_move=0.10,
            mean_1d_move=0.05,
            total_vol24=500.0,
            open_market_count=1,
        )
        ranked = to_ranked(candidate, metrics)

        assert ranked.ticker == "KXTEST"
        assert ranked.score == pytest.approx(composite_score(metrics))
        assert ranked.metrics.max_1d_move == 0.10


class TestPhase01Discover:
    @pytest.mark.asyncio
    async def test_filters_by_min_volume_and_sorts_desc(self):
        client = SimpleNamespace(
            get_series_list=AsyncMock(
                return_value=SimpleNamespace(
                    series=[
                        SimpleNamespace(
                            ticker="LOW",
                            title="Low Vol",
                            category="A",
                            frequency="daily",
                            tags=[],
                            volume_fp="500.00",
                            last_updated_ts=None,
                        ),
                        SimpleNamespace(
                            ticker="HIGH",
                            title="High Vol",
                            category="B",
                            frequency="daily",
                            tags=["x"],
                            volume_fp="10000.00",
                            last_updated_ts=None,
                        ),
                        SimpleNamespace(
                            ticker="MID",
                            title="Mid Vol",
                            category="C",
                            frequency="weekly",
                            tags=[],
                            volume_fp="2000.00",
                            last_updated_ts=None,
                        ),
                    ]
                )
            )
        )

        result = await discover_series(client, min_volume=1000)

        assert result.total_series_fetched == 3
        assert result.series_passing_volume_filter == 2
        assert [s.ticker for s in result.series] == ["HIGH", "MID"]
        assert result.series[0].volume == 10000.0


class TestPhase02Score:
    @pytest.mark.asyncio
    async def test_ranks_by_volatility_and_skips_no_open_markets(self, monkeypatch):
        candidates = [
            SeriesCandidate(
                ticker="QUIET",
                title="Quiet",
                category="A",
                frequency="daily",
                volume=1_000_000,
            ),
            SeriesCandidate(
                ticker="VOLATILE",
                title="Volatile",
                category="B",
                frequency="daily",
                volume=900_000,
            ),
            SeriesCandidate(
                ticker="EMPTY",
                title="Empty",
                category="C",
                frequency="daily",
                volume=800_000,
            ),
        ]

        async def fake_fetch(_client, series_ticker: str):
            if series_ticker == "EMPTY":
                return []
            if series_ticker == "VOLATILE":
                return [_market(bid="0.40", ask="0.50", last="0.90", previous="0.20", vol24="5000.00")]
            return [_market(bid="0.48", ask="0.52", last="0.50", previous="0.49", vol24="100.00")]

        score_module = importlib.import_module("app.etl.phases.phase_02_score.service")
        monkeypatch.setattr(score_module, "fetch_open_markets_for_series", fake_fetch)

        client = SimpleNamespace()
        result, store = await run_score_series(
            client,
            candidates,
            top_k=2,
            max_series_to_score=3,
            concurrency=1,
        )

        assert result.series_scored == 3
        assert result.series_skipped_no_open_markets == 1
        assert len(result.ranked_series) == 2
        assert result.ranked_series[0].ticker == "VOLATILE"
        assert result.ranked_series[0].score > result.ranked_series[1].score
        assert len(store) == 2
        assert len(store.get("VOLATILE")) == 1
        assert len(store.get("QUIET")) == 1
        assert store.get("EMPTY") == []


class TestPhase03Collect:
    def test_collect_markets_from_store(self):
        store = MarketsStore()
        store.put("VOLATILE", [_market(ticker="V1"), _market(ticker="V2")])
        store.put("QUIET", [_market(ticker="Q1")])

        from app.etl.phases.phase_02_score.models import (
            RankedSeries,
            SeriesRankingResult,
            SeriesVolatilityMetrics,
        )

        metrics = SeriesVolatilityMetrics(
            avg_spread=0.01,
            max_1d_move=0.1,
            mean_1d_move=0.05,
            total_vol24=100.0,
            open_market_count=2,
        )
        rankings = SeriesRankingResult(
            top_k=1,
            series_scored=2,
            series_skipped_no_open_markets=0,
            max_series_to_score=2,
            ranked_series=[
                RankedSeries(
                    ticker="VOLATILE",
                    title="Volatile",
                    category="A",
                    frequency="daily",
                    volume=1000.0,
                    score=5.0,
                    metrics=metrics,
                )
            ],
        )

        collected = collect_markets(rankings, store)

        assert collected.top_k == 1
        assert len(collected.series) == 1
        assert collected.series[0].series_ticker == "VOLATILE"
        assert collected.series[0].market_count == 2
        assert [m.ticker for m in collected.series[0].markets] == ["V1", "V2"]


class TestPhase04Routing:
    def test_candles_per_market_hourly_week(self):
        start = 0
        end = 7 * 86400
        assert candles_per_market(start, end, 60) == 168

    def test_max_tickers_per_batch_respects_candle_limit(self):
        start = 0
        end = 30 * 86400
        assert max_tickers_per_batch(start, end, 60) == 13

    def test_iter_time_windows_splits_long_ranges(self):
        start = 0
        period_seconds = 60 * 60
        end = 10_001 * period_seconds
        windows = list(iter_time_windows(start, end, 60))
        assert len(windows) == 2
        assert windows[0][0] == start
        assert windows[-1][1] == end
