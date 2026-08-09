from __future__ import annotations

from core.execution_plan import ExecutionPlan
from core.tools.path_policy import PathPolicy


class SecurityPolicy:
    """
    Política de seguridad para operaciones del sistema.

    Responsabilidades:
        - Verificar si una operación está permitida según el modo.
        - Controlar comandos shell, acceso a red, escritura, etc.
    """

    @staticmethod
    def is_allowed(operation: str, plan: ExecutionPlan) -> bool:
        """
        Verifica si una operación está permitida según el plan y el modo.

        Args:
            operation: "shell", "network", "write", "sudo"
            plan: ExecutionPlan actual (contiene governance)
        """
        mode = plan.governance.get("mode", "safe")

        if mode == "safe":
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
        """
        if plan.is_safe_mode() and command.strip().startswith("sudo"):
            return False, "sudo bloqueado en modo seguro."

        dangerous_patterns = ["rm -rf /", "dd if=", "mkfs"]
        for pattern in dangerous_patterns:
            if pattern in command:
                return False, f"Comando potencialmente peligroso bloqueado: {pattern}"

        return True, ""

    @staticmethod
    def check_path(path: str, plan: ExecutionPlan) -> tuple[bool, str]:
        """
        Verifica si se puede escribir en la ruta.
        """
        if not plan.allows_write():
            return False, "Escritura de archivos no permitida por la política del plan."

        ok, err = PathPolicy.validate(path)
        if not ok:
            return False, err

        return True, ""
