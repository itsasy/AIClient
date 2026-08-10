from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.project_inspector import ProjectInspector
from llm.router import LLMRouter
from skills.base import Skill

logger = logging.getLogger(__name__)


class PerformanceAuditSkill(Skill):
    """
    Audita el rendimiento del proyecto (tiempos de carga, uso de recursos, etc.).
    """

    name = "performance_audit"
    description = "Audita el rendimiento del proyecto."
    version = "2.0"
    capabilities = ("performance_audit",)

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
Eres un experto en rendimiento de software.

Audita el rendimiento del siguiente proyecto:

{snapshot.summary()}

Archivos relevantes:
{self._format_files(snapshot.files[:20])}

Analiza:
1. Potenciales cuellos de botella (base de datos, red, CPU, memoria).
2. Uso de recursos (caché, compresión, etc.).
3. Optimizaciones de código (bucles, algoritmos, etc.).
4. Recomendaciones para mejorar el rendimiento.

Genera un informe estructurado.
"""

            temp_plan = ExecutionPlan(
                original_task="Auditoría de rendimiento",
                intent="performance_audit",
            )

            snapshot = LLMRouter().generate(temp_plan, context={"instruction": prompt})

            files = [
                {
                    "path": getattr(f, "path", str(f)),
                    "lines": getattr(f, "lines", 0),
                }
                for f in (snapshot.files or [])[:50]
            ]

            evidence = {
                "type": "performance_evidence",
                "summary": snapshot.summary() if hasattr(snapshot, "summary") else "",
                "files": files,
                "file_count": len(files),
            }

            return {
                "ok": True,
                "result": evidence,
                "error": None,
            }
        except Exception as e:
            logger.exception("Error en PerformanceAuditSkill")
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
