from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class TestWorkflow(BaseWorkflow):
    """
    /test
    Ejecuta las pruebas del proyecto.
    """

    name = "test"
    description = "Ejecuta las pruebas del proyecto."

    def execute(self, arguments: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/test {arguments}" if arguments else "/test",
            intent="testing",
            intent_category="testing",
            objective="Ejecutar pruebas",
            execution_mode="multi_step",
        )

        # Paso 1: analizar qué pruebas ejecutar
        plan.add_step(
            description="Analizar qué pruebas ejecutar",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": arguments or "Ejecutar pruebas del proyecto",
            },
            expected_output="Plan de pruebas.",
            metadata={"stage": "test_analysis"},
        )

        # Paso 2: ejecutar pruebas
        plan.add_step(
            description="Ejecutar pruebas",
            unit_type="skill",
            unit_name="shell",
            params={
                "command": self._get_test_command(arguments),
            },
            expected_output="Resultado de las pruebas.",
            metadata={"stage": "test_execution"},
        )

        if len(plan.steps) >= 2:
            plan.steps[1].depends_on.append(plan.steps[0].id)

        plan.governance["allow_shell"] = True
        plan.context_requirements["project"] = True
        plan.metadata["requires_self_critic"] = True

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""

    def _get_test_command(self, arguments: str) -> str:
        if arguments:
            return arguments.strip()
        return "echo 'No hay pruebas configuradas'"
