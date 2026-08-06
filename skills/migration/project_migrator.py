from __future__ import annotations

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from core.project_inspector import ProjectInspector

from skills.base import Skill


class ProjectMigratorSkill(Skill):

    name = "migrate_project"

    description = "Analiza y prepara la migración " "de proyectos antiguos."

    version = "2.0"

    capabilities = (
        "project_migration",
        "architecture_review",
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

        old_project_path = params.get(
            "old_project_path",
            ".",
        )

        new_standards = params.get(
            "new_standards",
            ("Laravel 11, Docker, Sanctum, " "buenas prácticas modernas, " "arquitectura limpia"),
        )

        try:

            snapshot = self.inspector.inspect()

            return {
                "ok": True,
                "result": {
                    "type": "migration",
                    "snapshot": snapshot,
                    "old_project_path": old_project_path,
                    "new_standards": new_standards,
                },
                "error": None,
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
