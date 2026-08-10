from __future__ import annotations

import re
from typing import Any

from core.execution_plan import ExecutionPlan
from core.tools.path_policy import PathPolicy


class SecurityPolicy:
    """
    Política de seguridad transversal.

    Responsabilidades:
        - Verificar operaciones según governance del plan.
        - Bloquear comandos peligrosos y sudo en modo safe.
        - Validar rutas de escritura/lectura.
    """

    # Patrones destructivos (substring, case-insensitive)
    DANGEROUS_PATTERNS: tuple[str, ...] = (
        "rm -rf /",
        "rm -rf /*",
        "rm -fr /",
        "rm -fr /*",
        "dd if=",
        "mkfs",
        "mkfs.",
        ":(){:|:&};:",  # fork bomb
        "chmod -r 777 /",
        "chown -r ",
        "> /dev/sd",
        "mv /* ",
        "wget ",  # redirecciones peligrosas se miran aparte; listado mínimo
        "curl ",
    )

    # Prefijos siempre bloqueados en modo safe (aunque allow_shell=True)
    SAFE_MODE_BLOCKED_PREFIXES: tuple[str, ...] = (
        "sudo ",
        "sudo\t",
        "su ",
        "su\t",
        "doas ",
    )

    @staticmethod
    def is_allowed(operation: str, plan: ExecutionPlan) -> bool:
        """
        operation: "shell" | "network" | "write" | "sudo" | "read"
        """
        mode = (plan.governance or {}).get("mode", "safe")

        if mode != "safe":
            # modo powerful: aún se respetan flags explícitos del plan
            pass

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
        """
        Verifica un comando shell específico.
        Usar antes de cualquier ejecución real.
        """
        if not command or not str(command).strip():
            return False, "Comando vacío."

        cmd = str(command).strip()
        lower = cmd.lower()

        # 1. Governance: shell permitido
        if not SecurityPolicy.is_allowed("shell", plan):
            return False, "Ejecución de shell no permitida por la política del plan."

        # 2. sudo / elevación
        for prefix in SecurityPolicy.SAFE_MODE_BLOCKED_PREFIXES:
            if lower.startswith(prefix.strip()) or lower.startswith(prefix):
                if not plan.allows_sudo():
                    return False, "sudo/su bloqueado (allow_sudo=False o modo safe)."

        # 3. Patrones destructivos (siempre, incluso powerful)
        for pattern in SecurityPolicy.DANGEROUS_PATTERNS:
            if pattern.lower() in lower:
                return (
                    False,
                    f"Comando potencialmente peligroso bloqueado: patrón '{pattern}'.",
                )

        # 4. rm -rf con path raíz o vacío peligroso
        if re.search(r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|--force\s+)*(/|/\*|~|/home)\b", lower):
            return False, "rm destructivo sobre rutas de sistema bloqueado."

        return True, ""

    @staticmethod
    def check_path(path: str, plan: ExecutionPlan) -> tuple[bool, str]:
        """
        Verifica si se puede escribir (o crear) en la ruta.
        """
        if not SecurityPolicy.is_allowed("write", plan):
            return False, "Escritura de archivos no permitida por la política del plan."

        ok, err = PathPolicy.validate(path)
        if not ok:
            return False, err or "Ruta no permitida."

        return True, ""

    @staticmethod
    def check_read_path(path: str, plan: ExecutionPlan | None = None) -> tuple[bool, str]:
        """
        Lectura: exige estar dentro del proyecto.
        """
        ok, err = PathPolicy.validate(path)
        if not ok:
            return False, err or "Ruta de lectura no permitida."
        return True, ""
