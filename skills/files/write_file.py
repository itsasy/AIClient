from __future__ import annotations

from pathlib import Path
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.tools.path_policy import PathPolicy
from core.tools.security_policy import SecurityPolicy
from skills.base import Skill


class WriteFileSkill(Skill):
    """
    Skill para escribir archivos de forma segura.

    Contrato:
        - Solo escribe el contenido recibido.
        - No genera contenido.
        - No llama al LLM.
        - Valida rutas con PathPolicy y SecurityPolicy.
    """

    name = "write_file"
    description = "Escribe contenido en un archivo del sistema."
    version = "2.1"
    capabilities = ("file_write",)

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        params = step.params or {}
        path = params.get("path")
        content = params.get("content")

        if not path:
            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó una ruta de archivo.",
            }

        if content is None:
            return {
                "ok": False,
                "result": None,
                "error": "No se proporcionó contenido para escribir.",
            }

        # Seguridad de ruta (governance + path traversal)
        ok, error = SecurityPolicy.check_path(str(path), plan)
        if not ok:
            return {
                "ok": False,
                "result": None,
                "error": error,
            }

        if not plan.allows_write():
            return {
                "ok": False,
                "result": None,
                "error": "Política de escritura no permitida en este plan.",
            }

        try:
            normalized_path = PathPolicy.normalize(path)

            # Doble check post-normalize
            if not PathPolicy.is_within_project(normalized_path):
                return {
                    "ok": False,
                    "result": None,
                    "error": (f"Path traversal bloqueado: '{path}' " f"→ '{normalized_path}'"),
                }

            normalized_path.parent.mkdir(parents=True, exist_ok=True)
            normalized_path.write_text(str(content), encoding="utf-8")

            # Preferir path relativo al proyecto en el resultado
            try:
                rel = str(normalized_path.relative_to(PathPolicy.project_root()))
            except ValueError:
                rel = str(normalized_path)

            return {
                "ok": True,
                "result": {
                    "path": rel,
                    "absolute_path": str(normalized_path),
                    "size": len(str(content)),
                },
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "result": None,
                "error": f"Error al escribir archivo: {e}",
            }
