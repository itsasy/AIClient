from __future__ import annotations

from typing import Any

from core.project_inspector import ProjectInspector

from skills.base import Skill


class ProjectAnalyzerSkill(Skill):

    name = "analyze_project"

    description = "Analiza la estructura " "de un proyecto existente."

    version = "1.0"

    capabilities = ["project_analysis"]

    def __init__(self):

        self.inspector = ProjectInspector()

    def execute(
        self,
        **kwargs: Any,
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
