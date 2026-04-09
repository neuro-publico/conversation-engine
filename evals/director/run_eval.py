"""CLI runner del eval harness del Director Creativo.

Uso:

    # Correr todos los casos contra Gemini real (consume créditos):
    python -m evals.director.run_eval

    # Correr un solo caso por id:
    python -m evals.director.run_eval --case mosquitos_repelente

    # Output a archivo distinto:
    python -m evals.director.run_eval --out evals/director/reports/run_2026-04-06.json

Reportes se escriben a evals/director/reports/{timestamp}.json e incluyen:

  - resumen: count, pass_rate, avg_total, p50/p95 latency
  - per-case: pattern elegido, scores del judge, validators del director,
    latency, error si aplica

Variables de entorno requeridas:
  - GOOGLE_GEMINI_API_KEY  (para el director y el judge)
  - HOST_AGENT_CONFIG       (para cargar el agente video_director_animated_v1)

Este script vive bajo evals/ porque NO debe correr en CI: consume créditos
reales y depende de servicios externos.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Permite correr como `python -m evals.director.run_eval` desde la raíz del repo.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.requests.video_studio_draft_request import VideoStudioDraftRequest  # noqa: E402
from app.services.video_studio_service import VideoStudioError, VideoStudioService  # noqa: E402
from evals.director.judge import judge_safe  # noqa: E402

logger = logging.getLogger("evals.director")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CASES_PATH = Path(__file__).parent / "cases.json"
REPORTS_DIR = Path(__file__).parent / "reports"


def _load_cases(filter_id: Optional[str]) -> List[Dict[str, Any]]:
    with CASES_PATH.open() as f:
        data = json.load(f)
    cases = data.get("cases", [])
    if filter_id:
        cases = [c for c in cases if c["id"] == filter_id]
        if not cases:
            raise SystemExit(f"No case found with id '{filter_id}'")
    return cases


async def _run_one(case: Dict[str, Any], service: VideoStudioService) -> Dict[str, Any]:
    case_id = case["id"]
    logger.info("[EVAL] running case=%s", case_id)

    request = VideoStudioDraftRequest(
        reference_id=f"eval-{case_id}-{int(time.time())}",
        owner_id="eval-harness",
        product_name=case["product_name"],
        product_description=case.get("product_description", ""),
        duration=case.get("duration", 30),
        language=case.get("language", "es"),
    )

    t0 = time.monotonic()
    payload_dict: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    error_step: Optional[str] = None

    try:
        payload = await service.run_director(request)
        payload_dict = payload.model_dump()
    except VideoStudioError as e:
        error = str(e)
        error_step = e.step
        logger.warning("[EVAL] case=%s director failed step=%s err=%s", case_id, e.step, e)
    except Exception as e:  # pragma: no cover - defensive
        error = f"unexpected: {e}"
        error_step = "unknown"
        logger.error("[EVAL] case=%s unexpected error: %s", case_id, e)

    director_ms = int((time.monotonic() - t0) * 1000)

    judge_result: Dict[str, Any] = await judge_safe(
        product_name=case["product_name"],
        product_description=case.get("product_description", ""),
        director_payload=payload_dict,
    )

    return {
        "case_id": case_id,
        "expected_pattern_hint": case.get("expected_pattern_hint"),
        "selected_pattern_key": (payload_dict or {}).get("selected_pattern_key"),
        "director_latency_ms": director_ms,
        "director_ok": error is None,
        "director_error": error,
        "director_error_step": error_step,
        "judge": judge_result,
        "payload": payload_dict,
    }


def _summarize(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    director_ok = sum(1 for r in results if r["director_ok"])
    judge_passed = sum(1 for r in results if r["judge"].get("passed"))

    judge_totals = [r["judge"].get("total", 0.0) for r in results if r["director_ok"]]
    latencies = [r["director_latency_ms"] for r in results if r["director_ok"]]

    summary: Dict[str, Any] = {
        "cases_run": total,
        "director_pass_rate": round(director_ok / total, 3) if total else 0.0,
        "judge_pass_rate": round(judge_passed / total, 3) if total else 0.0,
        "avg_judge_total": round(statistics.mean(judge_totals), 2) if judge_totals else 0.0,
    }
    if latencies:
        sorted_lat = sorted(latencies)
        p50 = sorted_lat[len(sorted_lat) // 2]
        p95_idx = max(0, int(len(sorted_lat) * 0.95) - 1)
        summary["latency_p50_ms"] = p50
        summary["latency_p95_ms"] = sorted_lat[p95_idx]
    return summary


async def _async_main(filter_id: Optional[str], out_path: Optional[Path]) -> int:
    if not os.getenv("GOOGLE_GEMINI_API_KEY"):
        logger.error("GOOGLE_GEMINI_API_KEY no está seteada. Abortando.")
        return 2
    if not os.getenv("HOST_AGENT_CONFIG"):
        logger.error("HOST_AGENT_CONFIG no está seteada. Abortando.")
        return 2

    cases = _load_cases(filter_id)
    service = VideoStudioService()

    results: List[Dict[str, Any]] = []
    for case in cases:
        result = await _run_one(case, service)
        results.append(result)

    summary = _summarize(results)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    report = {
        "generated_at": timestamp,
        "summary": summary,
        "results": results,
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    final_out = out_path or (REPORTS_DIR / f"{timestamp}.json")
    with final_out.open("w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    logger.info("[EVAL] report written to %s", final_out)
    logger.info("[EVAL] summary: %s", json.dumps(summary, indent=2))
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Eval harness del Director Creativo")
    parser.add_argument("--case", help="Correr solo el case con este id")
    parser.add_argument("--out", type=Path, help="Path del reporte (default: evals/director/reports/{ts}.json)")
    args = parser.parse_args()

    exit_code = asyncio.run(_async_main(args.case, args.out))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
