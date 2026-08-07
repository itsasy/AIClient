from __future__ import annotations
from typing import Any
from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from llm.router import LLMRouter


class ArchitectAgent(Agent):
    name = "architect"
    role = "Arquitecto de Software"

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> str:
        context = {
            **(context or {}),
            "agent_role": {
                "name": self.name,
                "responsibility": (
                    "Analizar requisitos, diseñar soluciones "
                    "y definir decisiones arquitectónicas."
                ),
                "priorities": [
                    "Clean Architecture",
                    "SOLID",
                    "DDD",
                    "Escalabilidad",
                    "Mantenibilidad",
                    "Seguridad",
                ],
            },
        }
        return LLMRouter.generate(plan=plan, context=context)
