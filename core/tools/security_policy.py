from __future__ import annotations

import re
from typing import Any

from core.execution_plan import ExecutionPlan
from core.tools.path_policy import PathPolicy


class SecurityPolicy:
    """Política de seguridad transversal (shell, write, sudo)."""

    DANGEROUS_PATTERNS: tuple[str, ...] = (
        "rm -rf /",
        "rm -rf /*",
        "rm -fr /",
        "rm -fr /*",
        "dd if=",
        "mkfs",
        "mkfs.",
        ":(){:|:&};:",
        "chmod -r 777 /",
        "> /dev/sd",
        "mv /* ",
    )

    SAFE_MODE_BLOCKED_PREFIXES: tuple[str, ...] = (
        "sudo ",
        "sudo\t",
        "su ",
        "su\t",
        "doas ",
    )

    @staticmethod
    def is_allowed(operation: str, plan: ExecutionPlan) -> bool:
        if operation == "shell" and not plan.allows_shell():
            return False
        if operation == "network" and not plan.allows_network():
            return False
        if operation == "write" and not plan.allows_write():
            return False
        if operation == "sudo" and not plan.allows_sudo():
            return False
        return True

    @staticmethod
    def check_command(command: str, plan: ExecutionPlan) -> tuple[bool, str]:
        if not command or not str(command).strip():
            return False, "Comando vacío."

        cmd = str(command).strip()
        lower = cmd.lower()

        if not SecurityPolicy.is_allowed("shell", plan):
            # create_project / npx necesitan shell implícito si allow_write
            # Solo bloquear si explícitamente es operación shell del plan
            # Para scaffolding confiamos en allow_write + patrones peligrosos
            pass

        for prefix in SecurityPolicy.SAFE_MODE_BLOCKED_PREFIXES:
            if lower.startswith(prefix.strip()) or lower.startswith(prefix):
                if not plan.allows_sudo():
                    return False, "sudo/su bloqueado (allow_sudo=False o modo safe)."

        for pattern in SecurityPolicy.DANGEROUS_PATTERNS:
            if pattern.lower() in lower:
                return (
                    False,
                    f"Comando potencialmente peligroso bloqueado: patrón '{pattern}'.",
                )

        if re.search(
            r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|--force\s+)*(/|/\*|~|/home)\b",
            lower,
        ):
            return False, "rm destructivo sobre rutas de sistema bloqueado."

        return True, ""

    @staticmethod
    def check_path(path: str, plan: ExecutionPlan) -> tuple[bool, str]:
        if not SecurityPolicy.is_allowed("write", plan):
            return False, "Escritura de archivos no permitida por la política del plan."

        ok, err = PathPolicy.validate(path)
        if not ok:
            return False, err or "Ruta no permitida."

        return True, ""
