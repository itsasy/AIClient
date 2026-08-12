from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class TestWorkflow(BaseWorkflow):
    """
    /test [comando]

    Ejecuta la suite de tests del proyecto (o el comando indicado).
    Por defecto: pytest -q
    """

    name = "test"
    description = "Ejecuta tests del proyecto."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        cmd = (arguments or "").strip() or "pytest -q"

        plan = ExecutionPlan(
            original_task=f"/test {cmd}".strip(),
            intent="testing",
            intent_category="testing",
            objective=f"Ejecutar tests: {cmd}",
            execution_mode="single",
        )

        plan.context_requirements["project"] = False
        plan.governance["allow_shell"] = True

        plan.set_execution_unit(
            unit_type="skill",
            unit_name="shell",
            params={"command": cmd},
        )

        plan.metadata["workflow"] = "test"
        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        # /test sin args → pytest por defecto
        return True, ""
