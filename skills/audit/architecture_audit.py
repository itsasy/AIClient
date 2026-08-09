from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.project_inspector import ProjectInspector
from llm.router import LLMRouter
from skills.base import Skill

logger = logging.getLogger(__name__)


class ArchitectureAuditSkill(Skill):
    """
    Audita la arquitectura del proyecto (patrones, acoplamiento, etc.).
    """

    name = "architecture_audit"
    description = "Audita la arquitectura del proyecto."
    version = "2.0"
    capabilities = ("architecture_audit",)

    def __init__(self):
        self.inspector = ProjectInspector()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            snapshot = self.inspector.inspect_snapshot()

            prompt = f"""
Eres un arquitecto de software.

Audita la arquitectura del siguiente proyecto:

{snapshot.summary()}

Archivos relevantes:
{self._format_files(snapshot.files[:20])}

Analiza:
1. Separación de responsabilidades.
2. Patrones de diseño utilizados.
3. Acoplamiento y cohesión.
4. Modularidad y escalabilidad.
5. Deuda técnica arquitectónica.
6. Recomendaciones para mejorar la arquitectura.

Genera un informe estructurado.
"""

            temp_plan = ExecutionPlan(
                original_task="Auditoría de arquitectura",
                intent="architecture_audit",
            )
            response = LLMRouter().generate(temp_plan, context={"instruction": prompt})

            return {
                "ok": True,
                "result": {
                    "type": "architecture_audit",
                    "report": response,
                    "summary": "Auditoría de arquitectura completada.",
                },
                "error": None,
            }
        except Exception as e:
            logger.exception("Error en ArchitectureAuditSkill")
            return {
                "ok": False,
                "result": None,
                "error": str(e),
            }

    def _format_files(self, files: list) -> str:
        lines = []
        for f in files[:20]:
            lines.append(f"- {f.path} ({f.lines} líneas)")
        return "\n".join(lines) if lines else "No se encontraron archivos."
