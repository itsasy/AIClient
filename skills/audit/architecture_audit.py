from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.project_inspector import ProjectInspector
from skills.base import Skill

logger = logging.getLogger(__name__)


class ArchitectureAuditSkill(Skill):
    """
    Recolecta evidencia estructural del proyecto para auditoría arquitectónica.

    Contrato (goals.md):
        - NO llama al LLM.
        - NO razona.
        - Solo inspecciona y devuelve datos estructurados.
        - El razonamiento lo realiza un Agent (p. ej. ArchitectAgent).
    """

    name = "architecture_audit"
    description = (
        "Recolecta evidencia de arquitectura del proyecto " "(estructura, archivos, dependencias)."
    )
    version = "2.1"
    capabilities = (
        "architecture_audit",
        "evidence_collection",
    )

    def __init__(self) -> None:
        self.inspector = ProjectInspector()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            snapshot = self.inspector.inspect_snapshot()

            files = [
                {
                    "path": getattr(f, "path", str(f)),
                    "lines": getattr(f, "lines", 0),
                }
                for f in (snapshot.files or [])[:50]
            ]

            evidence = {
                "type": "architecture_evidence",
                "summary": snapshot.summary() if hasattr(snapshot, "summary") else "",
                "files": files,
                "file_count": len(files),
                "root": getattr(snapshot, "root", None),
            }

            return {
                "ok": True,
                "result": evidence,
                "error": None,
            }

        except Exception as e:
            logger.exception("Error en ArchitectureAuditSkill")
            return {
                "ok": False,
                "result": None,
                "error": str(e),
            }
