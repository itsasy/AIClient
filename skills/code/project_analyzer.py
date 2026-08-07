from __future__ import annotations

import logging
from typing import Any

from core.project_inspector import ProjectInspector
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill

logger = logging.getLogger(__name__)


class ProjectAnalyzerSkill(Skill):

    name = "analyze_project"

    description = "Analiza la estructura, arquitectura y contenido de un proyecto existente."

    version = "2.0"

    capabilities = (
        "project_analysis",
        "repository_inspection",
        "architecture_discovery",
    )

    def __init__(self) -> None:
        self.inspector = ProjectInspector()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        try:
            snapshot = self.inspector.inspect(
                path=params.get("path"),
            )

            return {
                "ok": True,
                "result": {
                    "type": "project_analysis",
                    "snapshot": snapshot,
                    "metadata": {
                        "skill": self.name,
                        "version": self.version,
                    },
                },
                "error": None,
            }

        except Exception as exc:

            logger.exception("Error analizando proyecto")

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
