from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import Any

from core.execution_result import ExecutionResult

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
    "failed": {
        "running",
    },
    "completed": set(),
    "skipped": set(),
}


VALID_UNIT_TYPES = {
    "agent",
    "skill",
}


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad individual dentro de un ExecutionPlan.

    Representa una acción concreta.

    Puede ser:

    - Agent.
    - Skill.

    No:

    - Ejecuta la acción.
    - Selecciona executor.
    - Construye contexto.
    - Gestiona pipeline.
    """

    # ==================================================
    # Identity
    # ==================================================

    id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    # ==================================================
    # Definition
    # ==================================================

    description: str = ""

    unit_type: str = ""

    unit_name: str = ""

    params: dict[str, Any] = field(
        default_factory=dict,
    )

    # ==================================================
    # Dependencies
    # ==================================================

    depends_on: list[str] = field(
        default_factory=list,
    )

    # ==================================================
    # Runtime state
    # ==================================================

    status: str = "pending"

    result: ExecutionResult | None = None

    error: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    # ==================================================
    # Lifecycle
    # ==================================================

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in VALID_STEP_STATUS:

            raise ValueError(f"Estado de step inválido: {status}")

        allowed = VALID_STEP_TRANSITIONS.get(
            self.status,
            set(),
        )

        if self.status != status and status not in allowed:

            raise ValueError(f"Transición inválida {self.status} -> {status}")

        self.status = status

    def mark_running(
        self,
    ) -> None:

        self.set_status(
            "running",
        )

    def mark_completed(
        self,
        result: ExecutionResult | None = None,
    ) -> None:

        self.set_status(
            "completed",
        )

        self.result = result

        self.error = None

    def mark_failed(
        self,
        error: str,
        result: ExecutionResult | None = None,
    ) -> None:

        self.set_status(
            "failed",
        )

        self.error = error

        self.result = result

    def skip(
        self,
    ) -> None:

        self.set_status(
            "skipped",
        )

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

        if self.unit_type not in VALID_UNIT_TYPES:

            errors.append(f"unit_type inválido: {self.unit_type}")

        if not self.unit_name.strip():

            errors.append(
                "step sin unit_name",
            )

        if self.status not in VALID_STEP_STATUS:

            errors.append(f"status inválido: {self.status}")

        if self.id in self.depends_on:

            errors.append(
                "step no puede depender de sí mismo",
            )

        if len(self.depends_on) != len(set(self.depends_on)):

            errors.append(
                "dependencias duplicadas",
            )

        if self.status == "completed" and not self.result:

            errors.append(
                "step completado requiere resultado",
            )

        if self.status == "failed" and not self.error:

            errors.append(
                "step fallido requiere error",
            )

        return errors

    # ==================================================
    # Helpers
    # ==================================================

    def is_ready(
        self,
        completed_steps: set[str],
    ) -> bool:

        return all(dependency in completed_steps for dependency in self.depends_on)

    def reset(
        self,
    ) -> None:

        self.status = "pending"

        self.result = None

        self.error = None

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "id": self.id,
            "description": self.description,
            "unit_type": self.unit_type,
            "unit_name": self.unit_name,
            "params": dict(self.params),
            "depends_on": list(self.depends_on),
            "status": self.status,
            "result": (self.result.to_dict() if self.result else None),
            "error": self.error,
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }
