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
    "cancelled",
}


VALID_UNIT_TYPES = {
    "agent",
    "skill",
    "tool",
    "workflow",
}


UNIT_ALIASES = {
    "agents": "agent",
    "agent_runtime": "agent",
    "skills": "skill",
    "skill_runtime": "skill",
    "tools": "tool",
    "workflows": "workflow",
}


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad mínima ejecutable.

    Representa:

    - Skill.
    - Agent.
    - Tool.
    - Workflow.

    No:

    - Ejecuta.
    - Resuelve dependencias.
    - Maneja resultados globales.
    """

    id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
    )

    trace_id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
    )

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

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    started_at: datetime | None = None

    completed_at: datetime | None = None

    def __post_init__(self):

        self.unit_type = self.normalize_unit_type(self.unit_type)

        if self.unit_name:
            self.unit_name = self.unit_name.strip()

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

    def validate(
        self,
    ) -> list[str]:

        errors = []

        if not self.description.strip():
            errors.append("step sin descripción")

        if self.unit_type not in VALID_UNIT_TYPES:
            errors.append("tipo de unidad inválido")

        if not self.unit_name:
            errors.append("unidad sin nombre")

        if self.timeout <= 0:
            errors.append("timeout inválido")

        if self.retries is not None and self.retries < 0:
            errors.append("retries inválido")

        return errors

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in VALID_STEP_STATUS:
            raise ValueError(f"Estado inválido: {status}")

        self.status = status

    def mark_running(self):

        self.set_status("running")

        self.started_at = datetime.now(timezone.utc)

    def mark_completed(
        self,
        result: Any = None,
    ):

        self.set_status("completed")

        self.result = result

        self.completed_at = datetime.now(timezone.utc)

    def mark_failed(
        self,
        error: str,
    ):

        self.set_status("failed")

        self.error = error

        self.completed_at = datetime.now(timezone.utc)
