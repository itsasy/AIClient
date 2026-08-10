from __future__ import annotations

from typing import Any

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from llm.router import LLMRouter


class MultiTurnAgent(Agent):
    """
    Agente conversacional.

    Para conversación pura solo necesita:
      - la tarea del usuario
      - historial (si existe)

    No debe recibir el ExecutionPlan completo como materia de análisis.
    """

    name = "multi_turn"
    role = "Agente conversacional"
    version = "2.1"

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> str:
        context = dict(context or {})

        history = context.get("memory") or context.get("conversation_history") or ""

        lean_context: dict[str, Any] = {
            "conversation_history": history,
            "agent_role": {
                "name": self.name,
                "responsibility": (
                    "Responder de forma natural, clara y útil a la "
                    "consulta del usuario. No analices el ExecutionPlan "
                    "ni la infraestructura interna del sistema."
                ),
            },
            "requested_output": {
                "format": "natural_language",
                "rules": [
                    "Responde directamente al usuario.",
                    "No menciones plan_id, intent, unit_type ni metadata interna.",
                    "No inventes capacidades del sistema que no te pidan.",
                ],
            },
        }

        for key in ("standards", "engram"):
            if context.get(key):
                lean_context[key] = context[key]

        return LLMRouter().generate(
            plan=plan,
            context=lean_context,
        )
