from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class BuildWorkflow(BaseWorkflow):
    """
    /build
    Construye el proyecto actual (ejecuta dependencias, compila, etc.)
    """

    name = "build"
    description = "Construye el proyecto actual."

    def execute(self, arguments: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/build {arguments}" if arguments else "/build",
            intent="build",
            intent_category="execution",
            objective="Construir el proyecto",
            execution_mode="single",
            execution_unit_type="skill",
            execution_unit="shell",
            params={
                "command": self._get_build_command(arguments),
            },
        )

        plan.governance["allow_shell"] = True
        plan.context_requirements["project"] = True

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""

    def _get_build_command(self, arguments: str) -> str:
        if arguments:
            return arguments.strip()
        return "echo 'Build no configurado'"
