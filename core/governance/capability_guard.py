from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class CapabilityError(PermissionError):
    """Se lanza cuando una capacidad requerida no está permitida."""


class CapabilityGuard:
    """
    Única puerta de acceso a capacidades peligrosas.

    Todas las Skills que tocan filesystem, shell, network o sudo
    DEBEN pasar por este guard antes de ejecutar la acción real.
    """

    # Mapeo de capabilities → método de governance del plan
    CAPABILITY_CHECKS = {
        "file_write": "allows_write",
        "file_read": "allows_read",
        "file_delete": "allows_write",  # delete también requiere write
        "shell": "allows_shell",
        "network": "allows_network",
        "sudo": "allows_sudo",
    }

    def __init__(self) -> None:
        self._audit_log: list[dict[str, Any]] = []

    # ---------------------------------------------------------
    # API pública
    # ---------------------------------------------------------

    def require(
        self,
        plan: ExecutionPlan,
        capability: str,
        *,
        actor: str | None = None,
        resource: str | None = None,
        reason: str | None = None,
    ) -> None:
        """
        Verifica que el plan permite la capacidad solicitada.
        Si no la permite, lanza CapabilityError.
        Siempre registra el intento en el audit log.
        """
        capability = capability.strip().lower()

        allowed = self._is_allowed(plan, capability)

        event = {
            "event": "capability_check",
            "capability": capability,
            "allowed": allowed,
            "actor": actor or "unknown",
            "resource": resource,
            "reason": reason,
            "plan_id": getattr(plan, "id", None),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._audit_log.append(event)

        if not allowed:
            msg = (
                f"Capacidad '{capability}' denegada por governance "
                f"(plan={getattr(plan, 'id', '?')})."
            )
            logger.warning(msg)
            raise CapabilityError(msg)

        logger.debug(
            "CapabilityGuard ALLOW | capability=%s | actor=%s | resource=%s",
            capability,
            actor,
            resource,
        )

    def require_write(
        self,
        plan: ExecutionPlan,
        *,
        actor: str | None = None,
        path: str | None = None,
    ) -> None:
        self.require(
            plan,
            "file_write",
            actor=actor,
            resource=path,
            reason="write_file",
        )

    def require_read(
        self,
        plan: ExecutionPlan,
        *,
        actor: str | None = None,
        path: str | None = None,
    ) -> None:
        self.require(
            plan,
            "file_read",
            actor=actor,
            resource=path,
            reason="read_file",
        )

    def require_shell(
        self,
        plan: ExecutionPlan,
        *,
        actor: str | None = None,
        command: str | None = None,
    ) -> None:
        self.require(
            plan,
            "shell",
            actor=actor,
            resource=command,
            reason="shell_execution",
        )

    def require_network(
        self,
        plan: ExecutionPlan,
        *,
        actor: str | None = None,
        url: str | None = None,
    ) -> None:
        self.require(
            plan,
            "network",
            actor=actor,
            resource=url,
            reason="network_access",
        )

    def require_sudo(
        self,
        plan: ExecutionPlan,
        *,
        actor: str | None = None,
    ) -> None:
        self.require(
            plan,
            "sudo",
            actor=actor,
            reason="sudo_required",
        )

    # ---------------------------------------------------------
    # Audit
    # ---------------------------------------------------------

    def get_audit_log(self) -> list[dict[str, Any]]:
        return list(self._audit_log)

    def clear_audit_log(self) -> None:
        self._audit_log.clear()

    # ---------------------------------------------------------
    # Internals
    # ---------------------------------------------------------

    def _is_allowed(self, plan: ExecutionPlan, capability: str) -> bool:
        method_name = self.CAPABILITY_CHECKS.get(capability)

        if method_name is None:
            # Capacidad desconocida → denegar por defecto
            logger.warning(
                "CapabilityGuard: capacidad desconocida '%s' → DENY",
                capability,
            )
            return False

        checker = getattr(plan, method_name, None)
        if callable(checker):
            try:
                return bool(checker())
            except Exception as exc:
                logger.exception(
                    "Error al consultar governance.%s: %s",
                    method_name,
                    exc,
                )
                return False

        # Fallback: si el plan tiene governance dict
        governance = getattr(plan, "governance", None)
        if isinstance(governance, dict):
            # Convención: allow_write, allow_shell, etc.
            key = method_name.replace("allows_", "allow_")
            return bool(governance.get(key, False))

        # Por defecto denegar
        return False
