from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import Any

VALID_STEP_STATUS = {
    "pending",
    "running",
    "completed",
    "failed",
    "skipped",
}


VALID_STEP_TRANSITIONS = {
    "pending": {
        "running",
        "skipped",
    },
    "running": {
        "completed",
        "failed",
    },
    "completed": set(),
    "failed": {
        "running",
    },
    "skipped": set(),
}


UNIT_TYPES = {
    "agent",
    "skill",
}


UNIT_ALIASES = {
    "agents": "agent",
    "agent_runtime": "agent",
    "skills": "skill",
    "skill_runtime": "skill",
}


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad atómica de ejecución.

    Representa una acción dentro de un ExecutionPlan.

    Responsabilidades:

    - Identificar unidad ejecutora.
    - Mantener parámetros.
    - Mantener estado.
    - Mantener dependencias.
    - Registrar metadata.

    No:

    - Ejecuta Agents.
    - Ejecuta Skills.
    - Decide workflows.
    """

    description: str = ""

    unit_type: str = ""

    unit_name: str = ""

    params: dict[str, Any] = field(
        default_factory=dict,
    )

    depends_on: list[str] = field(
        default_factory=list,
    )

    id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
    )

    status: str = "pending"

    result: Any = None

    error: str | None = None

    retries: int | None = None

    timeout: int = 60

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )

    # ==================================================
    # Initialization
    # ==================================================

    def __post_init__(
        self,
    ) -> None:

        self.unit_type = self.normalize_unit_type(
            self.unit_type,
        )

    # ==================================================
    # Normalization
    # ==================================================

    @classmethod
    def normalize_unit_type(
        cls,
        unit_type: str | None,
    ) -> str:

        if not unit_type:

            return ""

        value = unit_type.lower().strip().replace("-", "_").replace(" ", "_")

        return UNIT_ALIASES.get(
            value,
            value,
        )

    # ==================================================
    # Lifecycle
    # ==================================================

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in VALID_STEP_STATUS:

            raise ValueError(
                f"Estado inválido: {status}",
            )

        allowed = VALID_STEP_TRANSITIONS.get(
            self.status,
            set(),
        )

        if self.status != status and status not in allowed:

            raise ValueError(
                f"Transición inválida {self.status} -> {status}",
            )

        self.status = status

    def mark_running(
        self,
    ) -> None:

        self.set_status(
            "running",
        )

    def mark_completed(
        self,
        result: Any = None,
    ) -> None:

        self.set_status(
            "completed",
        )

        self.result = result

        self.error = None

    def mark_failed(
        self,
        error: str,
    ) -> None:

        self.set_status(
            "failed",
        )

        self.error = error

    def mark_skipped(
        self,
        reason: str | None = None,
    ) -> None:

        self.set_status(
            "skipped",
        )

        self.metadata["skip_reason"] = reason

    # ==================================================
    # Validation
    # ==================================================

    def validate(
        self,
    ) -> list[str]:

        errors: list[str] = []

        if not self.description.strip():

            errors.append(
                "step sin descripción",
            )

        if not self.unit_type:

            errors.append(
                "step sin tipo de unidad",
            )

        elif self.unit_type not in UNIT_TYPES:

            errors.append(
                "tipo de unidad inválido",
            )

        if not self.unit_name.strip():

            errors.append(
                "step sin unidad asignada",
            )

        if self.timeout <= 0:

            errors.append(
                "timeout inválido",
            )

        if self.retries is not None and self.retries < 0:

            errors.append(
                "retries inválido",
            )

        if len(self.depends_on) != len(set(self.depends_on)):

            errors.append(
                "dependencias duplicadas",
            )

        return errors

    # ==================================================
    # Utilities
    # ==================================================

    def clone(
        self,
    ) -> "ExecutionStep":

        import copy

        return copy.deepcopy(
            self,
        )
