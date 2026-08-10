from __future__ import annotations

from typing import Any

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from llm.router import LLMRouter


class TaskAgent(Agent):
    """
    Agente general de resolución.

    Responsabilidades:
        - Resolver tareas que requieren razonamiento general.
        - Consumir ExecutionPlan.
        - Consumir contexto preparado por ContextManager.
        - Delegar generación al LLMRouter.

    No:
        - Analiza intención.
        - Construye ExecutionPlans.
        - Selecciona contexto.
        - Gestiona memoria.
    """

    name = "task_agent"
    role = "Agente general de resolución"

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> str:
        context = dict(context or {})

        return LLMRouter().generate(
            plan=plan,
            context=context,
        )
