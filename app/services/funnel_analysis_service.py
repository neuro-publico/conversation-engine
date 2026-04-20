import asyncio
import json
import logging
import time
from typing import Any, Dict

from app.configurations.funnel_benchmarks import classify_all_rates, get_profile_thresholds
from app.db.audit_logger import log_prompt
from app.externals.ai_direct.gemini_text import GeminiTextError, call_gemini_structured
from app.requests.analyze_funnel_request import AnalyzeFunnelRequest
from app.responses.analyze_funnel_response import AnalyzeFunnelResponse
from app.services.funnel_analysis_service_interface import FunnelAnalysisServiceInterface

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Eres el "Cerebro Estratégico" de Fluxi, un consultor de Growth Senior audaz y orientado a resultados financieros. Tu misión no es reportar números, es DETENER EL SANGRADO DE DINERO y ESCALAR VENTAS.

TU MENTALIDAD:
- **Obsesión por la Rentabilidad:** Un clic barato no paga facturas. Una venta sí. Prioriza siempre las métricas más cercanas al dinero (ROAS, compras, CPC) sobre métricas de vanidad (impresiones, alcance).
- **Drama Calculado:** El usuario necesita sentir el dolor de perder dinero para actuar. No digas "El CTR es bajo". Di: "Estás pagando por impresiones que nadie cliquea — cada $1 gastado aquí se pierde."
- **Precisión Quirúrgica:** Odias los consejos genéricos como "mejora el anuncio". Amas lo específico: "Cambia los primeros 3 segundos del video", "Reduce el texto del copy a la mitad", "Prueba un hook con pregunta directa".

REGLAS DE ANÁLISIS (JERARQUÍA DE FLUXI):

1. **DETECTAR LA FUGA DE DINERO (Prioridad #1):**
   - Busca la métrica más costosa que está fallando.
   - Si ROAS < 1.5, ES UNA EMERGENCIA. El anuncio está perdiendo dinero.
   - Si CPC es alto pero CTR es bajo, el anuncio no convence.
   - Si Hook Rate es bajo, los primeros segundos del video fallan.
   - *Cálculo de Impacto:* Estima cuánto dinero se pierde. Ejemplo: "Con un CPC de $2.50 y solo 3 compras, estás gastando $X por cada venta."

2. **PROTEGE LOS ACTIVOS (Lo que funciona):**
   - Si una métrica es VERDE, ORDÉNALO EXPLÍCITAMENTE: "¡NO TOQUES ESTO!"
   - Muchos usuarios arruinan sus mejores anuncios por intentar optimizarlos. Tu deber es detenerlos.

3. **DIAGNÓSTICO CRUZADO (Contexto):**
   - Hook Rate Alto + CTR Bajo = "Tu video promete pero aburre antes del CTA" → Acción: Acortar video, mover CTA antes.
   - CTR Alto + Compras Bajas = "El anuncio atrae pero la landing no convierte" → Acción: Revisar landing page, precio, oferta.
   - ROAS Alto + Pocas impresiones = "Anuncio rentable pero sin escala" → Acción: Aumentar presupuesto gradualmente.
   - Hook Rate Bajo + CPC Alto = "Estás pagando por un video que nadie ve" → Acción: Cambiar los primeros 3 segundos.

INSTRUCCIONES DE RESPUESTA:

- **Para el "Headline":** Una frase de 6-8 palabras que resuma la situación del anuncio. Ej: "Video fuerte pero checkout débil".
- **Para "Critical Bottleneck":** El problema #1 del anuncio. Debe incluir impacto financiero que duela.
- **Para "Winning Assets":** Métricas sanas — palmada en la espalda al usuario.
- **Para "Secondary Optimizations":** Mejoras de menor prioridad.
- **Para "Today Checklist":** 3-5 acciones concretas y atómicas que el usuario puede hacer HOY.

Responde SIEMPRE en español, en JSON estructurado según el schema proporcionado."""


RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "analysis_summary": {
            "type": "object",
            "properties": {
                "headline": {"type": "string"},
                "overall_health_score": {"type": "integer", "minimum": 1, "maximum": 10},
            },
            "required": ["headline", "overall_health_score"],
        },
        "critical_bottleneck": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "financial_impact_text": {"type": "string"},
                "diagnosis": {"type": "string"},
                "action_plan": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "financial_impact_text", "diagnosis", "action_plan"],
        },
        "winning_assets": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "asset_name": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["asset_name", "message"],
            },
        },
        "secondary_optimizations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string"},
                    "advice": {"type": "string"},
                },
                "required": ["metric", "advice"],
            },
        },
        "today_checklist": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "analysis_summary",
        "critical_bottleneck",
        "winning_assets",
        "secondary_optimizations",
        "today_checklist",
    ],
}


class FunnelAnalysisService(FunnelAnalysisServiceInterface):
    """Agent that analyzes ad funnel metrics and returns a strategic action plan.

    Ported from the n8n workflow "Identificar constraints y prioridades". Uses
    Gemini Flash for structured JSON output with the semáforo (traffic-light)
    thresholds applied before the LLM call.
    """

    MODEL = "gemini-flash-latest"

    async def analyze(self, request: AnalyzeFunnelRequest) -> AnalyzeFunnelResponse:
        t_start = time.monotonic()

        rates_dict = request.rates.model_dump()
        semaforo = classify_all_rates(request.benchmark_profile, rates_dict)
        thresholds = get_profile_thresholds(request.benchmark_profile) or {}

        user_message = self._build_user_message(request, semaforo, thresholds)

        try:
            parsed, raw_response = await call_gemini_structured(
                model=self.MODEL,
                system_prompt=SYSTEM_PROMPT,
                user_message=user_message,
                response_schema=RESPONSE_SCHEMA,
                temperature=0.2,
                top_p=0.95,
                max_output_tokens=4096,
                thinking_level="High",
            )
        except GeminiTextError as e:
            logger.error("Gemini call failed for funnel analysis: %s", e)
            asyncio.create_task(
                log_prompt(
                    log_type="funnel_analysis",
                    prompt=user_message[:5000],
                    response_text=(e.raw or "")[:5000],
                    model=self.MODEL,
                    provider="gemini",
                    status="error",
                    error_message=str(e),
                    elapsed_ms=int((time.monotonic() - t_start) * 1000),
                    metadata={"ad_id": request.ad.ad_id, "benchmark_profile": request.benchmark_profile},
                )
            )
            raise

        asyncio.create_task(
            log_prompt(
                log_type="funnel_analysis",
                prompt=user_message[:5000],
                response_text=json.dumps(parsed, ensure_ascii=False)[:5000],
                model=self.MODEL,
                provider="gemini",
                status="success",
                elapsed_ms=int((time.monotonic() - t_start) * 1000),
                metadata={"ad_id": request.ad.ad_id, "benchmark_profile": request.benchmark_profile},
            )
        )

        return AnalyzeFunnelResponse(**parsed, semaforo=semaforo)

    def _build_user_message(
        self,
        request: AnalyzeFunnelRequest,
        semaforo: Dict[str, str],
        thresholds: Dict[str, Dict[str, float]],
    ) -> str:
        payload = {
            "ad": request.ad.model_dump(),
            "raw": request.raw.model_dump(),
            "rates": request.rates.model_dump(),
            "semaforo": semaforo,
            "thresholds": thresholds,
        }
        return (
            "Analiza este anuncio usando el semáforo ya calculado y devuelve el plan de acción. "
            "Datos del anuncio:\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
