from __future__ import annotations

from pathlib import Path
from typing import Any

from core.document_ingestor import DocumentIngestor

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

from skills.base import Skill


class IngestDocumentSkill(Skill):

    name = "ingest"

    description = "Ingiere un documento " "(PDF, DOCX, TXT, imagen) y lo guarda en Engram."

    version = "2.0"

    capabilities = (
        "document_ingestion",
        "knowledge_storage",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        filepath = params.get(
            "filepath",
            "",
        )

        tags = params.get(
            "tags",
            "",
        )

        if not filepath:

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó filepath.",
            }

        path = Path(filepath).expanduser()

        if not path.exists():

            return {
                "ok": False,
                "result": {
                    "type": "ingest_result",
                    "filepath": str(path),
                },
                "error": f"Archivo no encontrado: {filepath}",
            }

        tag_list = []

        if tags:

            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        try:

            ingestor = DocumentIngestor()

            success = ingestor.ingest_file(
                path,
                tags=tag_list,
            )

            return {
                "ok": success,
                "result": {
                    "type": "ingest_result",
                    "filepath": str(path),
                    "filename": path.name,
                    "tags": tag_list,
                },
                "error": (None if success else "Error ingiriendo documento."),
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
