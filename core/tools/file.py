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

    @staticmethod
    def _resolve_target(path: str | Path) -> Path:
        root = Path(Config.TARGET_PROJECT_ROOT).expanduser().resolve()
        candidate = Path(path).expanduser()

        if candidate.is_absolute():
            filepath = candidate.resolve()
        else:
            filepath = (root / candidate).resolve()

        if not filepath.is_relative_to(root):
            raise ValueError(f"Ruta fuera del proyecto bloqueada: {filepath}")

        return filepath

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
                "error": f"Operación no soportada: {operation}",
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
            filepath = self._resolve_target(path)

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
