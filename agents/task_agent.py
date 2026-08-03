from __future__ import annotations

from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan

from llm.router import LLMRouter


class TaskAgent(Agent):
    """
    Agente general de resolución.

    Responsabilidades:

    - Ejecutar solicitudes generales.
    - Delegar generación al LLMRouter.
    - Consumir ExecutionPlan y contexto.

    No:

    - Analiza intención.
    - Construye planes.
    - Gestiona memoria.
    """

    name = "task"

    role = "Agente general de resolución"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = context or {}

        return LLMRouter.generate(
            plan=plan,
            context=context,
        )
