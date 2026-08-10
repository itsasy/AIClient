from __future__ import annotations
from typing import Any
from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from llm.router import LLMRouter


class CoderAgent(Agent):
    name = "coder"
    role = "Generador e Implementador de Código"

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> str:
        context = dict(context or {})
        context["agent_role"] = {
            "name": self.name,
            "responsibility": "Implementar soluciones técnicas siguiendo el ExecutionPlan.",
            "priorities": [
                "Código limpio",
                "Buenas prácticas",
                "Testing",
                "Seguridad",
                "Legibilidad",
                "Compatibilidad con arquitectura existente",
            ],
        }
        return LLMRouter().generate(plan=plan, context=context)

    def validate_plan(self, plan: ExecutionPlan) -> list[str]:
        errors = []
        if not plan.params.get("task") and not plan.original_task:
            errors.append("CoderAgent requiere una tarea de implementación.")
        if not plan.steps and not plan.execution_unit:
            errors.append("CoderAgent requiere pasos definidos o una unidad de ejecución.")
        return errors
