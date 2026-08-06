from __future__ import annotations

from pathlib import Path

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.base import Skill


class WriteFileSkill(Skill):

    name = "write_file"

    description = "Escribe contenido en un archivo. " "No genera contenido."

    version = "2.0"

    capabilities = (
        "file_write",
        "filesystem_operation",
    )

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        params = step.params or {}

        path = params.get(
            "path",
            "",
        )

        content = params.get(
            "content",
            "",
        )

        if not content:

            return {
                "ok": False,
                "result": None,
                "error": ("No se proporcionó contenido " "para escribir."),
            }

        if not path:

            return {
                "ok": False,
                "result": None,
                "error": ("No se proporcionó ruta " "del archivo."),
            }

        try:

            filepath = Path(path).expanduser().resolve()

            filepath.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            filepath.write_text(
                content,
                encoding="utf-8",
            )

            return {
                "ok": True,
                "result": {
                    "type": "write_file_result",
                    "path": str(filepath),
                },
                "error": None,
            }

        except Exception as exc:

            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
