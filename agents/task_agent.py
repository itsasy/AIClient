from __future__ import annotations
from typing import Any
from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from llm.router import LLMRouter


class TaskAgent(Agent):
    name = "task_agent"
    role = "Agente general de resolución"

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> str:
        context = context or {}
        return LLMRouter.generate(plan=plan, context=context)
