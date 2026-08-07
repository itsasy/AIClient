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
    Inspecciona el proyecto y produce un contexto estructurado.

    El snapshot completo queda disponible para el runtime.

    El contexto arquitectónico que se entrega al siguiente Agent
    es deliberadamente compacto.
    """

    name = "analyze_project"

    description = "Analiza la estructura, archivos y arquitectura " "de un proyecto existente."

    version = "2.2"

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
            snapshot = self.inspector.inspect_snapshot()

            architecture_context = snapshot.to_architecture_context()

            logger.info(
                "Project snapshot generado | " "files=%s | directories=%s",
                snapshot.file_count,
                snapshot.directory_count,
            )

            return {
                "ok": True,
                "result": {
                    "type": "project_analysis",
                    # Resumen humano.
                    "summary": snapshot.summary(),
                    # Contexto compacto para Agents.
                    "architecture_context": architecture_context,
                    # Snapshot estructural.
                    #
                    # No contiene el contenido de archivos en la
                    # representación arquitectónica.
                    "snapshot": snapshot.to_dict(
                        include_content=False,
                    ),
                },
                "error": None,
            }

        except Exception as exc:
            logger.exception(
                "Error analizando proyecto",
            )

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
