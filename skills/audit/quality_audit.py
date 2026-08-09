from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.project_inspector import ProjectInspector
from llm.router import LLMRouter
from skills.base import Skill

logger = logging.getLogger(__name__)


class QualityAuditSkill(Skill):
    """
    Audita la calidad del código (complejidad, duplicación, cobertura, etc.).
    """

    name = "quality_audit"
    description = "Audita la calidad del código del proyecto."
    version = "2.0"
    capabilities = ("quality_audit",)

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
Eres un experto en calidad de software.

Audita la calidad del código del siguiente proyecto:

{snapshot.summary()}

Archivos relevantes:
{self._format_files(snapshot.files[:20])}

Analiza:
1. Complejidad ciclomática y mantenibilidad.
2. Duplicación de código.
3. Cobertura de pruebas (si existe).
4. Cumplimiento de estándares (Clean Code, SOLID, etc.).
5. Deuda técnica.
6. Recomendaciones para mejorar la calidad.

Genera un informe estructurado.
"""

            temp_plan = ExecutionPlan(
                original_task="Auditoría de calidad",
                intent="quality_audit",
            )
            response = LLMRouter().generate(temp_plan, context={"instruction": prompt})

            return {
                "ok": True,
                "result": {
                    "type": "quality_audit",
                    "report": response,
                    "summary": "Auditoría de calidad completada.",
                },
                "error": None,
            }
        except Exception as e:
            logger.exception("Error en QualityAuditSkill")
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
