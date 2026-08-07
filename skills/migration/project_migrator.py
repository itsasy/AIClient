from __future__ import annotations

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from core.project_inspector import ProjectInspector

from skills.base import Skill


class ProjectMigratorSkill(Skill):

    name = "migrate_project"

    description = "Migra proyecto antiguo a estándares modernos."

    version = "2.0"

    capabilities = (
        "project_migration",
        "architecture_upgrade",
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

        old_project_path = params.get(
            "old_project_path",
            ".",
        )

        new_standards = params.get(
            "new_standards",
            "",
        )

        try:

            snapshot = self.inspector.inspect()

            return {
                "ok": True,
                "result": {
                    "type": "migration",
                    "payload": {
                        "snapshot": snapshot,
                        "new_standards": (
                            new_standards
                            or (
                                "Laravel 11, Docker, Sanctum, "
                                "buenas prácticas modernas, "
                                "arquitectura limpia"
                            )
                        ),
                        "old_project_path": old_project_path,
                    },
                },
                "error": None,
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
