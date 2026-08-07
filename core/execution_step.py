from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime

from typing import Any

VALID_STEP_STATUS = {
    "pending",
    "running",
    "completed",
    "failed",
    "cancelled",
}


VALID_UNIT_TYPES = {
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
    Unidad ejecutable dentro de un ExecutionPlan.

    Representa una acción concreta:
    - Agent.
    - Skill.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    description: str = ""

    unit_type: str | None = None

    unit_name: str | None = None

    params: dict[str, Any] = field(
        default_factory=dict,
    )

    expected_output: str | None = None

    retries: int | None = None

    timeout: int = 120

    depends_on: list[str] = field(
        default_factory=list,
    )

    status: str = "pending"

    result: Any = None

    error: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    started_at: datetime | None = None

    completed_at: datetime | None = None

    # ==================================================
    # Initialization
    # ==================================================

    def __post_init__(
        self,
    ) -> None:

        self.unit_type = self.normalize_unit_type(
            self.unit_type,
        )

        if self.unit_name:
            self.unit_name = self.unit_name.strip()

    # ==================================================
    # Normalization
    # ==================================================

    @classmethod
    def normalize_unit_type(
        cls,
        unit_type: str | None,
    ) -> str | None:

        if not unit_type:
            return None

        value = unit_type.lower().strip().replace("-", "_").replace(" ", "_")

        return UNIT_ALIASES.get(
            value,
            value,
        )

    # ==================================================
    # Validation
    # ==================================================

    def validate(
        self,
    ) -> list[str]:

        errors: list[str] = []

        if not self.description.strip():

            errors.append("step sin descripción")

        if self.unit_type not in VALID_UNIT_TYPES:

            errors.append("tipo de unidad inválido")

        if not self.unit_name:

            errors.append("unidad sin nombre")

        if self.retries is not None and self.retries < 0:

            errors.append("retries inválido")

        if self.timeout <= 0:

            errors.append("timeout inválido")

        for dependency in self.depends_on:

            if not dependency.strip():

                errors.append("dependencia inválida")

            if dependency == self.id:

                errors.append("step no puede depender de sí mismo")

        return errors

    # ==================================================
    # Lifecycle
    # ==================================================

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in VALID_STEP_STATUS:

            raise ValueError(f"Estado inválido: {status}")

        self.status = status

    def mark_running(
        self,
    ) -> None:

        self.set_status(
            "running",
        )

        self.started_at = datetime.now().astimezone()

    def mark_completed(
        self,
        result: Any = None,
    ) -> None:

        self.set_status(
            "completed",
        )

        self.result = result

        self.error = None

        self.completed_at = datetime.now().astimezone()

    def mark_failed(
        self,
        error: str,
    ) -> None:

        self.set_status(
            "failed",
        )

        self.error = error

        self.completed_at = datetime.now().astimezone()
