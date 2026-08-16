from __future__ import annotations

from typing import Any

from core.commands.workflow import BaseWorkflow
from core.execution_plan import ExecutionPlan


class ReviewWorkflow(BaseWorkflow):
    """
    /review [foco]

    Revisión de calidad/arquitectura del proyecto actual.
    Usa agents/skills existentes (no inventa unit "analyze").
    """

    name = "review"
    description = "Revisa el proyecto y sugiere mejoras."

    def execute(
        self,
        arguments: str,
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        focus = (arguments or "").strip() or "revisión general de calidad y arquitectura"

        plan = ExecutionPlan(
            original_task=f"/review {focus}".strip(),
            intent="project_analysis",
            intent_category="maintenance",
            objective=f"Revisar: {focus}",
            execution_mode="multi_step",
        )

        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True
        plan.context_requirements["engram"] = True

        inspect = plan.add_step(
            description="Inspeccionar proyecto",
            unit_type="skill",
            unit_name="analyze_project",
            params={"task": focus},
            expected_output="Evidencia estructural del proyecto.",
            metadata={
                "stage": "inspection",
                "produces": "project_analysis",
            },
        )

        review = plan.add_step(
            description=f"Evaluación: {focus}",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": (
                    f"Revisa el proyecto con foco en: {focus}.\n"
                    "Entrega hallazgos priorizados, riesgos y acciones concretas.\n"
                    "No inventes archivos que no estén en la evidencia."
                ),
            },
            expected_output="Informe de revisión ejecutivo.",
            metadata={"stage": "analysis"},
        )
        review.depends_on.append(inspect.id)

        plan.metadata["workflow"] = "review"
        plan.metadata["requires_self_critic"] = True
        return plan

    def validate(self, arguments: str) -> tuple[bool, str]:
        return True, ""
