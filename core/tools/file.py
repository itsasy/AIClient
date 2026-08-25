from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config import Config
from core.tools.base import Tool


class FileTool(Tool):
    name = "file"
    description = "Operaciones seguras sobre archivos."
    version = "2.1"
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
            raise ValueError(f"Ruta fuera del proyecto bloqueada: {filepath} (root={root})")
        if filepath == root:
            raise ValueError("No se puede usar el directorio raíz del proyecto como archivo.")
        return filepath

    def execute(
        self,
        operation: str,
        path: str,
        content: str = "",
        **kwargs: Any,
    ) -> dict[str, Any]:
        if operation != "write":
            return {
                "ok": False,
                "result": None,
                "error": f"Operación no soportada: {operation}",
            }

        if not path or not str(path).strip():
            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó ruta.",
            }

        if content is None or (isinstance(content, str) and content == ""):
            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó contenido.",
            }

        if not isinstance(content, str):
            content = str(content)

        try:
            root = Path(Config.TARGET_PROJECT_ROOT).expanduser().resolve()
            filepath = self._resolve_target(path)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(content, encoding="utf-8")
            rel = str(filepath.relative_to(root))
            return {
                "ok": True,
                "result": {
                    "path": rel,
                    "absolute_path": str(filepath),
                    "size": len(content.encode("utf-8")),
                },
                "error": None,
            }
        except Exception as exc:
            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }
