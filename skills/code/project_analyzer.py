from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.project_inspector import ProjectInspector
from skills.base import Skill

logger = logging.getLogger(__name__)


class ProjectAnalyzerSkill(Skill):
    """
    Inspecciona el proyecto y produce contexto estructurado.

    Params de step (opcionales):
      - path: ruta absoluta o relativa al root base
      - prefer_target / target: True → TARGET_PROJECT_ROOT
      - task: texto original (metadata)

    Sin flag explícito → prefer_target=True (producto / TARGET).
    """

    name = "analyze_project"
    description = (
        "Analiza la estructura, archivos y arquitectura de un proyecto existente."
    )
    version = "2.4"
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
        try:
            params = getattr(step, "params", None) or {}
            path = params.get("path")
            prefer_target = self._resolve_prefer_target(plan, params)

            snapshot = self.inspector.inspect_snapshot(
                path=path,
                prefer_target=prefer_target,
            )
            architecture_context = snapshot.to_architecture_context(
                max_files=80,
                max_directories=60,
                include_file_content=False,
            )

            logger.info(
                "Project snapshot generado | root=%s | files=%s | directories=%s | prefer_target=%s",
                snapshot.root_path,
                snapshot.file_count,
                snapshot.directory_count,
                prefer_target,
            )

            return {
                "ok": True,
                "result": {
                    "type": "project_analysis",
                    "summary": snapshot.summary(),
                    "architecture_context": architecture_context,
                    "snapshot": snapshot.to_dict(include_content=False),
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

    @staticmethod
    def _resolve_prefer_target(
        plan: ExecutionPlan,
        params: dict[str, Any],
    ) -> bool:
        if "prefer_target" in params:
            return bool(params.get("prefer_target"))
        if "target" in params:
            return bool(params.get("target"))

        task = str(
            params.get("task")
            or getattr(plan, "original_task", None)
            or ""
        ).lower()

        if any(
            token in task
            for token in (
                "aiclient",
                "orquestador",
                "analiza aiclient",
                "analizar aiclient",
            )
        ):
            return False

        return True