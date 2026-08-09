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
    version = "2.0"
    capabilities = ("file_write",)

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Escribe el contenido en la ruta especificada.

        Args:
            plan: ExecutionPlan actual (contiene governance y contexto).
            step: Paso actual (contiene params con "path" y "content").
            context: Contexto adicional (no usado aquí).

        Returns:
            dict con "ok", "result" y "error".
        """
        # 1. Obtener parámetros
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

        # 2. Validar seguridad de la ruta
        ok, error = SecurityPolicy.check_path(path, plan)
        if not ok:
            return {
                "ok": False,
                "result": None,
                "error": error,
            }

        # 3. Validar política de escritura
        if not plan.allows_write():
            return {
                "ok": False,
                "result": None,
                "error": "Política de escritura no permitida en este plan.",
            }

        # 4. Normalizar ruta y escribir
        try:
            normalized_path = PathPolicy.normalize(path)

            # Crear directorios si no existen
            normalized_path.parent.mkdir(parents=True, exist_ok=True)

            # Escribir contenido
            normalized_path.write_text(content, encoding="utf-8")

            return {
                "ok": True,
                "result": {
                    "path": str(normalized_path),
                    "size": len(content),
                },
                "error": None,
            }

        except Exception as e:
            return {
                "ok": False,
                "result": None,
                "error": f"Error al escribir archivo: {e}",
            }
