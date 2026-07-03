from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.ingest_service import build_ingest_response
from app.api.schemas import IngestRequest, IngestResponse
from app.etl.phases.phase_01_discover.models import SeriesCandidate, SeriesUniverseResult
from app.etl.phases.phase_02_score.models import (
    RankedSeries,
    SeriesRankingResult,
    SeriesVolatilityMetrics,
)
from app.etl.phases.phase_03_collect.models import CollectedMarketsResult, SeriesMarkets
from app.etl.phases.phase_04_history.models import (
    HistoryResult,
    MarketHistory,
    SeriesHistory,
)
from app.etl.run import PipelineResult
from app.main import app


def _metrics(**kwargs) -> SeriesVolatilityMetrics:
    defaults = dict(
        avg_spread=0.02,
        max_1d_move=0.15,
        mean_1d_move=0.05,
        total_vol24=1000.0,
        open_market_count=3,
    )
    defaults.update(kwargs)
    return SeriesVolatilityMetrics(**defaults)


def _sample_pipeline_result(*, through: int = 4) -> PipelineResult:
    universe = SeriesUniverseResult(
        min_volume=1000.0,
        total_series_fetched=100,
        series_passing_volume_filter=50,
        series=[
            SeriesCandidate(
                ticker="KXTEST",
                title="Test",
                category="Sports",
                frequency="daily",
                volume=5000.0,
            )
        ],
    )
    rankings = SeriesRankingResult(
        top_k=1,
        series_scored=10,
        series_skipped_no_open_markets=2,
        max_series_to_score=10,
        ranked_series=[
            RankedSeries(
                ticker="KXTEST",
                title="Test Series",
                category="Sports",
                frequency="daily",
                volume=5000.0,
                score=4.5,
                metrics=_metrics(),
            )
        ],
    )
    collected = CollectedMarketsResult(
        top_k=1,
        series=[
            SeriesMarkets(
                series_ticker="KXTEST",
                score=4.5,
                market_count=3,
                markets=[],
            )
        ],
    )
    history = HistoryResult(
        lookback_days=7,
        period_interval=60,
        start_ts=1,
        end_ts=2,
        max_markets_per_series=5,
        markets_fetched=3,
        series=[
            SeriesHistory(
                series_ticker="KXTEST",
                markets=[
                    MarketHistory(
                        ticker="MKT-1",
                        series_ticker="KXTEST",
                        candlestick_count=24,
                        candlesticks=[],
                    )
                ],
            )
        ],
    )

    return PipelineResult(
        universe=universe,
        rankings=rankings if through >= 2 else None,
        collected=collected if through >= 3 else None,
        history=history if through >= 4 else None,
    )


class TestIngestRequestSchema:
    def test_defaults(self):
        req = IngestRequest()
        assert req.through == 4
        assert req.persist is False
        assert req.min_volume is None

    def test_custom_values(self):
        req = IngestRequest(
            through=2,
            top_k=5,
            max_series_to_score=30,
            period_interval=1440,
            persist=True,
        )
        assert req.through == 2
        assert req.period_interval == 1440
        assert req.persist is True

    def test_through_out_of_range_rejected(self):
        with pytest.raises(ValidationError):
            IngestRequest(through=0)
        with pytest.raises(ValidationError):
            IngestRequest(through=5)

    def test_invalid_period_interval_rejected(self):
        with pytest.raises(ValidationError):
            IngestRequest(period_interval=30)  # type: ignore[arg-type]

    def test_json_round_trip(self):
        payload = {"through": 3, "top_k": 10, "persist": True}
        req = IngestRequest.model_validate(payload)
        assert req.model_dump() == {
            "through": 3,
            "min_volume": None,
            "top_k": 10,
            "max_series_to_score": None,
            "concurrency": None,
            "lookback_days": None,
            "period_interval": None,
            "max_markets_per_series": None,
            "candlestick_concurrency": None,
            "persist": True,
        }


class TestIngestResponseSchema:
    def test_build_response_full_pipeline(self):
        result = _sample_pipeline_result(through=4)
        response = build_ingest_response(result, through=4, duration_seconds=12.5)

        assert isinstance(response, IngestResponse)
        assert response.status == "completed"
        assert response.through == 4
        assert response.duration_seconds == 12.5
        assert response.phase_1.series_passing_volume_filter == 50
        assert response.phase_2 is not None
        assert len(response.phase_2.ranked_series) == 1
        assert response.phase_2.ranked_series[0].ticker == "KXTEST"
        assert response.phase_3 is not None
        assert response.phase_3.total_markets == 3
        assert response.phase_4 is not None
        assert response.phase_4.candlestick_count == 24

    def test_build_response_phase_1_only(self):
        result = _sample_pipeline_result(through=1)
        response = build_ingest_response(result, through=1, duration_seconds=1.0)

        assert response.phase_2 is None
        assert response.phase_3 is None
        assert response.phase_4 is None

    def test_response_json_schema_serializable(self):
        result = _sample_pipeline_result(through=4)
        response = build_ingest_response(result, through=4, duration_seconds=3.0)
        data = response.model_dump(mode="json")

        assert data["status"] == "completed"
        assert data["phase_2"]["ranked_series"][0]["score"] == 4.5
        roundtrip = IngestResponse.model_validate(data)
        assert roundtrip == response


class TestIngestEndpoint:
    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_ingest_empty_body_uses_defaults(self, client):
        mock_response = build_ingest_response(
            _sample_pipeline_result(through=4),
            through=4,
            duration_seconds=1.0,
        )
        with patch(
            "app.api.routes.pipeline.run_ingest",
            new=AsyncMock(return_value=mock_response),
        ):
            resp = client.post("/api/v1/pipeline/ingest")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "completed"
        assert body["through"] == 4
        assert body["phase_1"]["series_passing_volume_filter"] == 50
        assert body["phase_4"]["candlestick_count"] == 24

    def test_ingest_with_request_body(self, client):
        mock_response = build_ingest_response(
            _sample_pipeline_result(through=2),
            through=2,
            duration_seconds=0.5,
        )
        with patch(
            "app.api.routes.pipeline.run_ingest",
            new=AsyncMock(return_value=mock_response),
        ):
            resp = client.post(
                "/api/v1/pipeline/ingest",
                json={"through": 2, "top_k": 5, "max_series_to_score": 20},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["through"] == 2
        assert body["phase_2"] is not None
        assert body["phase_3"] is None
        assert body["phase_4"] is None

    def test_ingest_invalid_body_returns_422(self, client):
        resp = client.post(
            "/api/v1/pipeline/ingest",
            json={"through": 99},
        )
        assert resp.status_code == 422

    def test_openapi_includes_ingest_schema(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/api/v1/pipeline/ingest" in schema["paths"]
        post = schema["paths"]["/api/v1/pipeline/ingest"]["post"]
        assert "IngestRequest" in post["requestBody"]["content"]["application/json"]["schema"].get(
            "$ref", ""
        ) or "IngestRequest" in str(post)
