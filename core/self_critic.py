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
    Etapa de evaluación post-ejecución.

    No es un agente; es una función del ExecutionEngine.
    """

    def evaluate(self, plan: ExecutionPlan, result: ExecutionResult) -> dict[str, Any]:
        """
        Evalúa el resultado de la ejecución y decide si es aceptable.
        """
        # Si el resultado ya falló, no criticar
        if result.is_failure:
            return {"pass": False, "reason": result.error or "Ejecución fallida"}

        # Si no se requiere crítica, pasar
        if not plan.metadata.get("requires_self_critic", False):
            return {"pass": True}

        # Construir prompt para crítica
        prompt = self._build_critique_prompt(plan, result)

        try:
            response = LLMRouter.generate(plan=plan, context={"draft_response": prompt})
            data = self._parse_response(response)
            return {
                "pass": data.get("pass", True),
                "reason": data.get("reason", ""),
                "score": data.get("score", 0),
            }
        except Exception:
            logger.exception("Error en SelfCritic")
            return {"pass": True, "reason": "Crítica no disponible"}

    def _build_critique_prompt(self, plan: ExecutionPlan, result: ExecutionResult) -> str:
        return f"""
Evalúa la calidad de la siguiente respuesta para la tarea:

Tarea original: {plan.original_task}

Intención: {plan.intent}

Resultado producido:
{json.dumps(result.to_dict(), indent=2, ensure_ascii=False)}

Devuelve un JSON con:
- "pass": true/false,
- "reason": explicación breve,
- "score": puntuación del 0 al 10.
"""

    def _parse_response(self, response: str) -> dict:
        start = response.find("{")
        end = response.rfind("}") + 1
        if start == -1 or end == -1:
            return {"pass": True, "reason": "", "score": 0}
        try:
            return json.loads(response[start:end])
        except Exception:
            return {"pass": True, "reason": "", "score": 0}
