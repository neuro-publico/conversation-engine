"""LLM-as-judge para puntuar el output del Director Creativo.

El judge usa Gemini con structured output forzado para puntuar 5 dimensiones
en escala 1-5. No mockeable: corre contra Gemini real y consume créditos.
Por eso vive bajo evals/ y NO bajo tests/ — no se ejecuta en CI.

Rúbrica (cada dimensión 1-5):

  - tonal_coherence: ¿concept + scripts + cinematic mantienen el mismo tono?
  - product_integration: ¿script_part_b incluye el producto literal y de forma natural?
  - cinematic_quality: ¿los cinematic prompts son ricos en verbos de acción y
    visualmente concretos? (no genéricos, no abstractos)
  - hook_strength: ¿el viral_hook_first_3_seconds engancha en los primeros 3s?
  - pattern_fit: ¿el pattern elegido encaja con el producto?

Score total: promedio de las 5 dimensiones. Threshold de baseline: ≥ 3.8
(3.8 sobre 5.0 = ~76%, suficiente para aprobar el draft).
"""

import json
from typing import Any, Dict, Optional

from app.externals.ai_direct.gemini_text import GeminiTextError, call_gemini_structured

JUDGE_MODEL = "gemini-3.1-pro-preview"

JUDGE_SYSTEM_PROMPT = """Sos un evaluador estricto de scripts publicitarios para video ads de e-commerce.

Tu trabajo es puntuar el output de un Director Creativo según una rúbrica fija. No
sos amable ni indulgente. Si un script es genérico, das 2. Si el cinematic dice
"camera moves", das 1. Solo das 5 a outputs sobresalientes.

DIMENSIONES (todas en escala 1-5, enteros):

1. tonal_coherence
   - 5: concept_visual_brief, script_part_a, script_part_b, cinematic_prompt_a y
        cinematic_prompt_b mantienen el mismo tono creativo (ej: todos sarcásticos
        o todos terroríficos o todos absurdos).
   - 1: hay disonancia tonal (ej: concept es horror pero script es comedia).

2. product_integration
   - 5: script_part_b incluye el nombre literal del producto de forma natural,
        sin sonar a slogan forzado.
   - 1: el producto no aparece o aparece como anuncio publicitario obvio.

3. cinematic_quality
   - 5: cinematic_prompt_a y _b son ricos en verbos de acción concretos
        (lurches, stalks, gasps, smirks, looms, cradles), describen plano + lente +
        movimiento + iluminación, y son visualmente reproducibles por Kling.
   - 1: prompts genéricos tipo "the camera moves around the product".

4. hook_strength
   - 5: viral_hook_first_3_seconds es una imagen/acción que genera curiosidad
        instantánea y haría parar el scroll.
   - 1: hook plano, descriptivo, "this is a product that helps you...".

5. pattern_fit
   - 5: el selected_pattern_key encaja perfecto con el producto y la audiencia.
        El selection_reasoning lo justifica claramente.
   - 1: pattern arbitrario, reasoning vacío o contradictorio.

Devolvé SOLO el JSON estructurado pedido por el responseSchema. Sin prosa extra.
"""

JUDGE_RESPONSE_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "tonal_coherence": {"type": "integer", "minimum": 1, "maximum": 5},
        "product_integration": {"type": "integer", "minimum": 1, "maximum": 5},
        "cinematic_quality": {"type": "integer", "minimum": 1, "maximum": 5},
        "hook_strength": {"type": "integer", "minimum": 1, "maximum": 5},
        "pattern_fit": {"type": "integer", "minimum": 1, "maximum": 5},
        "rationale": {"type": "string"},
    },
    "required": [
        "tonal_coherence",
        "product_integration",
        "cinematic_quality",
        "hook_strength",
        "pattern_fit",
        "rationale",
    ],
}


async def judge_director_payload(
    *,
    product_name: str,
    product_description: str,
    director_payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Puntuar un payload del director con LLM-as-judge.

    Returns:
        Dict con las 5 dimensiones (1-5), `rationale` (string), `total` (float)
        y `passed` (bool, total >= 3.8).

    Raises:
        GeminiTextError: si la llamada al judge falla después de los retries.
    """
    user_message = (
        f"Producto: {product_name}\n"
        f"Descripción: {product_description}\n\n"
        f"Output del Director Creativo a evaluar:\n"
        f"```json\n{json.dumps(director_payload, ensure_ascii=False, indent=2)}\n```\n\n"
        f"Puntuá según la rúbrica."
    )

    parsed, _raw = await call_gemini_structured(
        model=JUDGE_MODEL,
        system_prompt=JUDGE_SYSTEM_PROMPT,
        user_message=user_message,
        response_schema=JUDGE_RESPONSE_SCHEMA,
        temperature=0.2,
        top_p=0.8,
        max_output_tokens=1024,
        thinking_level="Medium",
    )

    scores = [
        parsed["tonal_coherence"],
        parsed["product_integration"],
        parsed["cinematic_quality"],
        parsed["hook_strength"],
        parsed["pattern_fit"],
    ]
    total = round(sum(scores) / len(scores), 2)

    return {
        **parsed,
        "total": total,
        "passed": total >= 3.8,
    }


async def judge_safe(
    *,
    product_name: str,
    product_description: str,
    director_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Wrapper que nunca lanza — devuelve un dict con error si falla."""
    if director_payload is None:
        return {"error": "no_payload", "passed": False, "total": 0.0}
    try:
        return await judge_director_payload(
            product_name=product_name,
            product_description=product_description,
            director_payload=director_payload,
        )
    except GeminiTextError as e:
        return {"error": f"judge_failed: {e}", "passed": False, "total": 0.0}
    except Exception as e:  # pragma: no cover - defensive
        return {"error": f"judge_unexpected: {e}", "passed": False, "total": 0.0}
