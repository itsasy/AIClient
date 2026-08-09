from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class ReviewWorkflow(BaseWorkflow):
    """
    /review
    Revisa el código generado (ejecuta SelfCritic sobre el resultado).
    """

    name = "review"
    description = "Revisa el código generado y sugiere mejoras."

    def execute(self, arguments: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/review {arguments}" if arguments else "/review",
            intent="review",
            intent_category="maintenance",
            objective="Revisar código",
            execution_mode="single",
            execution_unit_type="skill",
            execution_unit="analyze",
            params={
                "task": arguments or "Revisar el código generado",
            },
        )

        plan.context_requirements["project"] = True
        plan.metadata["requires_self_critic"] = True

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""
