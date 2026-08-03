from __future__ import annotations

from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan

from llm.router import LLMRouter


class MultiTurnAgent(Agent):
    """
    Agente conversacional con soporte de historial.

    Responsabilidades:

    - Consumir memoria proporcionada por ContextManager.
    - Enriquecer contexto conversacional.
    - Delegar generación al LLMRouter.

    No:

    - Guarda memoria.
    - Recupera contexto directamente.
    - Modifica ExecutionPlan.
    """

    name = "multi_turn"

    role = "Agente conversacional con memoria"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = context or {}

        history = context.get(
            "memory",
            "",
        )

        enriched_context = {
            **context,
            "conversation_history": history,
        }

        return LLMRouter.generate(
            plan=plan,
            context=enriched_context,
        )
