from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.project_inspector import ProjectInspector
from skills.base import Skill

logger = logging.getLogger(__name__)


class QualityAuditSkill(Skill):
    """
    Recolecta evidencia de calidad de código.
    NO razona. NO llama al LLM.
    """

    name = "quality_audit"
    description = "Recolecta evidencia de calidad del código del proyecto."
    version = "2.1"
    capabilities = (
        "quality_audit",
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
                "type": "quality_evidence",
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
            logger.exception("Error en QualityAuditSkill")
            return {
                "ok": False,
                "result": None,
                "error": str(e),
            }
