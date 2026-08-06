from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from core.project_inspector import ProjectInspector

from skills.base import Skill


class GenerateReadmeSkill(Skill):

    name = "readme"

    description = "Genera una estructura de README profesional " "basada en el proyecto real."

    version = "2.0"

    capabilities = (
        "documentation",
        "readme_generation",
        "project_analysis",
    )

    def __init__(self):

        self.inspector = ProjectInspector()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        request = params.get(
            "request",
            "",
        )

        description = params.get(
            "description",
            "",
        )

        try:

            snapshot = self.inspector.inspect()

            return {
                "ok": True,
                "result": {
                    "type": "readme",
                    "request": request,
                    "description": description,
                    "snapshot": snapshot,
                },
                "error": None,
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
