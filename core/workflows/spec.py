from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class SpecWorkflow(BaseWorkflow):
    """
    /spec <descripción>
    Genera una especificación (Spec) para una tarea.
    """

    name = "spec"
    description = "Genera una especificación formal para una tarea."

    def execute(self, arguments: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        plan = ExecutionPlan(
            original_task=f"/spec {arguments}",
            intent="spec",
            intent_category="planning",
            objective="Crear especificación formal",
            execution_mode="multi_step",
        )

        # El plan tiene un paso: generar la spec (usando un agente o LLM)
        plan.add_step(
            description=f"Generar especificación para: {arguments}",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": arguments,
                "mode": "spec",
            },
            expected_output="Especificación estructurada en formato JSON.",
            metadata={"stage": "spec_generation"},
        )

        # Luego, guardar la spec en disco
        plan.add_step(
            description="Guardar especificación en disco",
            unit_type="skill",
            unit_name="write_file",
            params={
                "path": f".specs/{self._sanitize_name(arguments)}.json",
                "content": "",
            },
            expected_output="Archivo de especificación creado.",
        )

        if len(plan.steps) >= 2:
            plan.steps[1].depends_on.append(plan.steps[0].id)

        plan.metadata["requires_self_critic"] = True

        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        if not arguments or not arguments.strip():
            return False, "Se requiere una descripción para /spec"
        return True, ""

    def _sanitize_name(self, name: str) -> str:
        """Convierte una descripción en un nombre de archivo seguro."""
        import re

        return re.sub(r"[^a-zA-Z0-9_\-]", "_", name[:50]).strip("_")
