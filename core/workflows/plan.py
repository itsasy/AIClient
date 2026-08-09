from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class PlanWorkflow(BaseWorkflow):
    """
    /plan
    Genera un plan de ejecución a partir de la tarea actual.
    """

    name = "plan"
    description = "Genera un plan de ejecución para la tarea actual."

    def execute(self, arguments: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/plan {arguments}" if arguments else "/plan",
            intent="planning",
            intent_category="planning",
            objective="Generar un plan de ejecución",
            execution_mode="multi_step",
        )

        # Usar el agente planner
        plan.add_step(
            description=f"Generar plan de ejecución para: {arguments or 'tarea actual'}",
            unit_type="agent",
            unit_name="planner",
            params={
                "task": arguments or "Generar un plan para la tarea actual",
            },
            expected_output="Plan de ejecución estructurado.",
            metadata={"stage": "plan_generation"},
        )

        plan.metadata["requires_self_critic"] = True

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""
