from __future__ import annotations
import json
import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class SelfCritic:
    """
    Etapa de evaluación post-ejecución con estructura detallada.

    Devuelve:
        {
            "pass": bool,
            "score": int (0-10),
            "issues": list[str],
            "corrections": list[str],
            "reason": str
        }
    """

    def evaluate(self, plan: ExecutionPlan, result: ExecutionResult) -> dict[str, Any]:
        """
        Evalúa el resultado de la ejecución y decide si es aceptable.
        """
        # Si el resultado ya falló, no criticar
        if result.is_failure:
            return {
                "pass": False,
                "score": 0,
                "issues": [result.error or "Ejecución fallida"],
                "corrections": [],
                "reason": result.error or "Ejecución fallida",
            }

        # Si no se requiere crítica, pasar
        if not plan.metadata.get("requires_self_critic", False):
            return {
                "pass": True,
                "score": 10,
                "issues": [],
                "corrections": [],
                "reason": "No se requirió crítica.",
            }

        # Construir prompt para crítica
        prompt = self._build_critique_prompt(plan, result)

        try:
            response = LLMRouter.generate(plan=plan, context={"draft_response": prompt})
            data = self._parse_response(response)

            # Asegurar que tiene todos los campos
            return {
                "pass": data.get("pass", True),
                "score": data.get("score", 5),
                "issues": data.get("issues", []),
                "corrections": data.get("corrections", []),
                "reason": data.get("reason", ""),
            }
        except Exception as e:
            logger.exception("Error en SelfCritic")
            return {
                "pass": True,
                "score": 5,
                "issues": ["Crítica no disponible"],
                "corrections": [],
                "reason": f"Error en crítica: {e}",
            }

    def _build_critique_prompt(self, plan: ExecutionPlan, result: ExecutionResult) -> str:
        return f"""
Evalúa la calidad de la siguiente respuesta para la tarea.

Tarea original: {plan.original_task}

Intención: {plan.intent}

Resultado producido:
{json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}

Devuelve un JSON con esta estructura:
{{
    "pass": true/false,
    "score": (0-10),
    "issues": ["problema1", "problema2"],
    "corrections": ["corrección1", "corrección2"],
    "reason": "explicación breve"
}}

Reglas:
- pass es True si el resultado es aceptable (score >= 5).
- score es una puntuación de 0 a 10.
- issues: lista de problemas detectados.
- corrections: lista de sugerencias de corrección (si pass es False, deben ser concretas).
- reason: resumen de la evaluación.
"""

    def _parse_response(self, response: str) -> dict:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start == -1 or end == -1:
            return {"pass": True, "score": 5, "issues": [], "corrections": [], "reason": ""}
        try:
            return json.loads(response[start:end])
        except Exception:
            return {"pass": True, "score": 5, "issues": [], "corrections": [], "reason": ""}
