from __future__ import annotations

from pathlib import Path

from typing import Any

from core.config import Config

from core.tools.base import Tool


class FileTool(Tool):

    name = "file"

    description = "Operaciones seguras sobre archivos."

    version = "2.0"

    capabilities = (
        "file_write",
        "filesystem_operation",
    )

    def execute(
        self,
        operation: str,
        path: str,
        content: str = "",
        **kwargs,
    ) -> dict[str, Any]:

        if operation != "write":

            return {
                "ok": False,
                "result": None,
                "error": (f"Operación no soportada: {operation}"),
            }

        if not path:

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó ruta.",
            }

        if not content:

            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó contenido.",
            }

        try:

            root = Path(Config.TARGET_PROJECT_ROOT).resolve()

            filepath = (root / path).resolve()

            if not str(filepath).startswith(str(root)):

                return {
                    "ok": False,
                    "result": None,
                    "error": ("Ruta fuera del proyecto bloqueada."),
                }

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
