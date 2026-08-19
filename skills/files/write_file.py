from __future__ import annotations

from typing import Any

from core.governance.capability_guard import (
    CapabilityGuard,
    CapabilityError,
)
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.tools.path_policy import PathPolicy
from core.tools.security_policy import SecurityPolicy
from skills.base import Skill


class WriteFileSkill(Skill):
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
        """
        Ejecuta la escritura de un archivo.

        Orden de seguridad:

            1. Validar parámetros.
            2. CapabilityGuard.
            3. SecurityPolicy.
            4. Política de escritura del plan.
            5. Normalizar path.
            6. Verificar límites del proyecto.
            7. Crear directorio.
            8. Escribir archivo.

        CapabilityGuard debe ejecutarse antes de cualquier
        operación que modifique el filesystem.
        """

        guard = CapabilityGuard()

        params = step.params or {}

        path = params.get("path")
        content = params.get("content")

        # ======================================================
        # Validación básica
        # ======================================================

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

        # ======================================================
        # Capability Guard
        # ======================================================
        #
        # IMPORTANTE:
        #
        # Esto debe ocurrir antes de cualquier modificación
        # del filesystem.
        #
        # CapabilityGuard es la autoridad que determina si
        # el actor está autorizado a realizar esta capacidad.
        #

        try:
            guard.require_write(
                plan,
                actor="write_file",
                path=path,
            )

        except CapabilityError as exc:
            return {
                "ok": False,
                "result": None,
                "error": str(exc),
            }

        # ======================================================
        # Security Policy
        # ======================================================

        ok, error = SecurityPolicy.check_path(
            str(path),
            plan,
        )

        if not ok:
            return {
                "ok": False,
                "result": None,
                "error": error,
            }

        # ======================================================
        # Plan write policy
        # ======================================================

        if not plan.allows_write():
            return {
                "ok": False,
                "result": None,
                "error": ("Política de escritura no permitida " "en este plan."),
            }

        # ======================================================
        # Path normalization + containment
        # ======================================================

        try:
            normalized_path = PathPolicy.normalize(
                path,
            )

            if not PathPolicy.is_within_project(
                normalized_path,
            ):
                return {
                    "ok": False,
                    "result": None,
                    "error": (f"Path traversal bloqueado: " f"'{path}' → '{normalized_path}'"),
                }

            # ==================================================
            # Filesystem mutation
            # ==================================================

            normalized_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            normalized_path.write_text(
                str(content),
                encoding="utf-8",
            )

            # ==================================================
            # Relative path
            # ==================================================

            try:
                rel = str(
                    normalized_path.relative_to(
                        PathPolicy.project_root(),
                    )
                )

            except ValueError:
                rel = str(
                    normalized_path,
                )

            return {
                "ok": True,
                "result": {
                    "path": rel,
                    "absolute_path": str(
                        normalized_path,
                    ),
                    "size": len(
                        str(content),
                    ),
                },
                "error": None,
            }

        except Exception as exc:
            return {
                "ok": False,
                "result": None,
                "error": (f"Error al escribir archivo: {exc}"),
            }
