# Eval harness — Director Creativo

Suite de evaluación offline para el `VideoStudioService` (Director Creativo).
Equivalente a tests unitarios pero para prompts: corre N casos canónicos contra
Gemini real y los puntúa con un LLM-as-judge.

**No corre en CI**. Consume créditos reales de Gemini y depende de
agent-config corriendo. Es una herramienta de iteración manual cuando se
modifica el system prompt o los `creative_patterns`.

## Estructura

- `cases.json` — casos canónicos (producto + duración + pattern esperado).
- `judge.py` — LLM-as-judge con rúbrica de 5 dimensiones (1-5).
- `run_eval.py` — runner CLI. Lee cases, corre el director, judgea, escribe reporte.
- `reports/` — outputs JSON con timestamp (gitignoreado).

## Cómo correr

Variables requeridas en el entorno:

```
export GOOGLE_GEMINI_API_KEY=...
export HOST_AGENT_CONFIG=https://agent-config-dev.fluxi.co
```

Correr todos los casos:

```
python -m evals.director.run_eval
```

Correr un solo caso por id:

```
python -m evals.director.run_eval --case mosquitos_repelente
```

Output a archivo distinto:

```
python -m evals.director.run_eval --out /tmp/eval-baseline.json
```

## Rúbrica del judge

Cada dimensión 1-5, total = promedio:

| Dimensión | Qué mide |
|---|---|
| `tonal_coherence` | Concept + scripts + cinematic mantienen el mismo tono |
| `product_integration` | Script B incluye nombre literal del producto, naturalmente |
| `cinematic_quality` | Verbos de acción concretos + plano + lente + iluminación |
| `hook_strength` | Primeros 3s parariían el scroll |
| `pattern_fit` | Pattern elegido encaja con el producto + reasoning sólido |

**Threshold de baseline**: `total ≥ 3.8` (3.8/5 = 76%). Por debajo de esto el
caso se considera fallado y hay que iterar el system prompt o los patterns.

## Workflow recomendado

1. Antes de tocar el system prompt, correr `run_eval.py` para snapshot baseline.
2. Modificar el prompt / agregar pattern nuevo en agent-config-front dev.
3. Correr `run_eval.py` de nuevo y comparar `summary` contra el baseline.
4. Si `avg_judge_total` bajó >0.3 puntos, **rollback**. Si subió, commit el cambio.

## Tests unitarios

Los tests con mocks viven en `tests/unit/services/test_video_studio_service.py`
y SÍ corren en CI. Cubren happy path combo/non-combo, validator self-correction,
agent_config sin patterns, y errores de Gemini.
