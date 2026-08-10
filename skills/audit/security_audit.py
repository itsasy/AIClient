from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.project_inspector import ProjectInspector
from llm.router import LLMRouter
from skills.base import Skill

logger = logging.getLogger(__name__)


class SecurityAuditSkill(Skill):
    """
    Realiza una auditoría de seguridad en el proyecto.
    """

    name = "security_audit"
    description = (
        "Audita la seguridad del proyecto (vulnerabilidades, dependencias, configuraciones)."
    )
    version = "2.0"
    capabilities = ("security_audit",)

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
Eres un experto en seguridad de software.

Realiza una auditoría de seguridad en el siguiente proyecto:

{snapshot.summary()}

Archivos relevantes (hasta 20):
{self._format_files(snapshot.files[:20])}

Analiza:
1. Vulnerabilidades comunes (inyección SQL, XSS, CSRF, etc.)
2. Dependencias obsoletas o con vulnerabilidades conocidas.
3. Configuraciones inseguras (claves en código, permisos, etc.)
4. Prácticas de seguridad (autenticación, autorización, cifrado).
5. Recomendaciones para mitigar riesgos.

Genera un informe estructurado con:
- Resumen ejecutivo
- Riesgos críticos
- Riesgos medios
- Riesgos bajos
- Recomendaciones prioritarias
"""

            temp_plan = ExecutionPlan(
                original_task="Auditoría de seguridad",
                intent="security_audit",
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
                "type": "security_evidence",
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
            logger.exception("Error en SecurityAuditSkill")
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
