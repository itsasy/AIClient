from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class PlanWorkflow(BaseWorkflow):
    """
    /plan [descripción]

    Genera un plan de ejecución legible (no ejecuta el plan generado).
    Usa task_agent (no existe agent "planner").
    """

    name = "plan"
    description = "Genera un plan de ejecución para la tarea actual."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        topic = (arguments or "").strip() or "la tarea actual del proyecto"

        plan = ExecutionPlan(
            original_task=f"/plan {topic}" if arguments else "/plan",
            intent="planning",
            intent_category="planning",
            objective=f"Generar plan de ejecución para: {topic}",
            execution_mode="single",
        )

        plan.context_requirements["project"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        plan.set_execution_unit(
            unit_type="agent",
            unit_name="task_agent",
            params={
                "task": (
                    f"Elabora un plan de ejecución paso a paso para: {topic}.\n\n"
                    "Formato:\n"
                    "1. Objetivo\n"
                    "2. Pasos numerados (qué hacer, en qué orden)\n"
                    "3. Dependencias entre pasos\n"
                    "4. Riesgos\n"
                    "5. Criterio de hecho\n\n"
                    "Sé concreto y técnico. No ejecutes nada; solo planifica."
                ),
                "mode": "planning",
            },
        )

        plan.metadata["requires_self_critic"] = False
        plan.metadata["workflow"] = "plan"

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""
