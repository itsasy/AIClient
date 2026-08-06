from __future__ import annotations

from typing import Any

from core.project_inspector import ProjectInspector

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class ProjectAnalyzerSkill(Skill):

    name = "analyze_project"

    description = "Analiza la estructura de un proyecto existente."

    version = "2.0"

    capabilities = (
        "project_analysis",
        "repository_inspection",
        "architecture_discovery",
    )

    def __init__(self):

        self.inspector = ProjectInspector()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        try:

            snapshot = self.inspector.inspect()

            return {
                "ok": True,
                "result": {
                    "type": "project_analysis",
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
