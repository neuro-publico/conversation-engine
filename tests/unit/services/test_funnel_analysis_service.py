from unittest.mock import AsyncMock, patch

import pytest

from app.requests.analyze_funnel_request import (
    AnalyzeFunnelRequest,
    FunnelAdContext,
    FunnelMetricsRates,
    FunnelMetricsRaw,
)
from app.services.funnel_analysis_service import FunnelAnalysisService


@pytest.fixture
def valid_request() -> AnalyzeFunnelRequest:
    return AnalyzeFunnelRequest(
        ad=FunnelAdContext(ad_id="123", ad_name="Test Ad", campaign_name="Test Campaign"),
        raw=FunnelMetricsRaw(
            impressions=50000,
            video_3s=12000,
            video_50=4500,
            link_clicks=800,
            spend=250.0,
            purchases=15,
            thruplay=3500,
        ),
        rates=FunnelMetricsRates(
            hook_rate=0.24,
            thruplay_rate=0.07,
            ctr=1.6,
            cpc=0.31,
            roas=2.8,
            click_to_purchase=0.019,
        ),
        benchmark_profile="dropshipping_prospecting",
    )


@pytest.fixture
def mock_gemini_response() -> dict:
    return {
        "analysis_summary": {
            "headline": "Video débil con conversión decente",
            "overall_health_score": 6,
        },
        "critical_bottleneck": {
            "title": "Hook Rate crítico",
            "financial_impact_text": "Estás perdiendo el 76% de las impresiones en los primeros 3 segundos.",
            "diagnosis": "El inicio del video no capta atención.",
            "action_plan": [
                "Cambia los primeros 3 segundos del video",
                "Prueba un hook con pregunta directa",
                "Agrega un movimiento visual fuerte al inicio",
            ],
        },
        "winning_assets": [{"asset_name": "CTR", "message": "¡NO TOQUES ESTO! Tu CTR es saludable."}],
        "secondary_optimizations": [{"metric": "ROAS", "advice": "Monitorea ROAS — está en zona amarilla."}],
        "today_checklist": [
            "Grabar 2 versiones nuevas del primer segundo del video",
            "Revisar top 3 hooks de la competencia",
            "Lanzar A/B test con el nuevo hook",
        ],
    }


class TestFunnelAnalysisService:
    async def test_analyze_returns_structured_response(self, valid_request, mock_gemini_response):
        service = FunnelAnalysisService()

        with patch(
            "app.services.funnel_analysis_service.call_gemini_structured",
            new=AsyncMock(return_value=(mock_gemini_response, {"raw": "response"})),
        ):
            response = await service.analyze(valid_request)

        assert response.analysis_summary.headline == "Video débil con conversión decente"
        assert response.analysis_summary.overall_health_score == 6
        assert response.critical_bottleneck.title == "Hook Rate crítico"
        assert len(response.critical_bottleneck.action_plan) == 3
        assert len(response.winning_assets) == 1
        assert len(response.today_checklist) == 3

    async def test_analyze_populates_semaforo_from_rates(self, valid_request, mock_gemini_response):
        service = FunnelAnalysisService()

        with patch(
            "app.services.funnel_analysis_service.call_gemini_structured",
            new=AsyncMock(return_value=(mock_gemini_response, {})),
        ):
            response = await service.analyze(valid_request)

        # hook_rate=0.24 → red (< 0.25)
        assert response.semaforo["hook_rate"] == "red"
        # ctr=1.6 → green (>= 1.5)
        assert response.semaforo["ctr"] == "green"
        # cpc=0.31 → green (<= 0.50)
        assert response.semaforo["cpc"] == "green"
        # roas=2.8 → yellow (>= 1.5 and < 3.0)
        assert response.semaforo["roas"] == "yellow"

    async def test_analyze_calls_gemini_with_flash_model(self, valid_request, mock_gemini_response):
        service = FunnelAnalysisService()

        mock_call = AsyncMock(return_value=(mock_gemini_response, {}))
        with patch("app.services.funnel_analysis_service.call_gemini_structured", new=mock_call):
            await service.analyze(valid_request)

        call_kwargs = mock_call.call_args.kwargs
        assert call_kwargs["model"] == "gemini-flash-latest"
        assert "Cerebro Estratégico" in call_kwargs["system_prompt"]

    async def test_analyze_sends_full_metrics_in_user_message(self, valid_request, mock_gemini_response):
        service = FunnelAnalysisService()

        mock_call = AsyncMock(return_value=(mock_gemini_response, {}))
        with patch("app.services.funnel_analysis_service.call_gemini_structured", new=mock_call):
            await service.analyze(valid_request)

        user_message = mock_call.call_args.kwargs["user_message"]
        # Should contain the raw metrics, rates, and semaforo classification
        assert '"hook_rate": 0.24' in user_message
        assert '"impressions": 50000' in user_message
        assert '"semaforo"' in user_message
