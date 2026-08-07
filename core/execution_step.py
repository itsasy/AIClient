from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad individual de trabajo dentro de un ExecutionPlan.

    La unidad ejecutable se identifica exclusivamente mediante:

        unit_type
        unit_name

    unit_type solo puede ser:
        agent
        skill

    Las herramientas (tools) se ejecutan a través de skills.
    """

    VALID_UNIT_TYPES = frozenset(
        {
            "agent",
            "skill",
        }
    )

    VALID_STATUSES = frozenset(
        {
            "pending",
            "running",
            "completed",
            "failed",
            "skipped",
        }
    )

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str
    unit_type: str
    unit_name: str
    params: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    expected_output: str | None = None
    retries: int = 0
    timeout: int = 120
    status: str = "pending"
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.description = self.description.strip()
        self.unit_type = self.unit_type.strip().lower()
        self.unit_name = self.unit_name.strip()

        if not self.description:
            raise ValueError("ExecutionStep requiere una descripción.")

        if self.unit_type not in self.VALID_UNIT_TYPES:
            raise ValueError(
                f"Tipo de unidad inválido: {self.unit_type}. "
                f"Tipos permitidos: {sorted(self.VALID_UNIT_TYPES)}"
            )

        if not self.unit_name:
            raise ValueError("ExecutionStep requiere un unit_name válido.")

        if self.retries < 0:
            raise ValueError("ExecutionStep.retries no puede ser negativo.")

        if self.timeout <= 0:
            raise ValueError("ExecutionStep.timeout debe ser mayor que cero.")

        if self.status not in self.VALID_STATUSES:
            raise ValueError(f"Estado de step inválido: {self.status}.")

    @property
    def is_terminal(self) -> bool:
        return self.status in {
            "completed",
            "failed",
            "skipped",
        }

    def mark_running(self) -> None:
        self.status = "running"
        self.error = None

    def mark_completed(self, result: Any = None) -> None:
        self.status = "completed"
        self.result = result
        self.error = None

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = error

    def mark_skipped(self, reason: str | None = None) -> None:
        self.status = "skipped"
        if reason:
            self.metadata["skip_reason"] = reason

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "unit_type": self.unit_type,
            "unit_name": self.unit_name,
            "params": dict(self.params),
            "depends_on": list(self.depends_on),
            "expected_output": self.expected_output,
            "retries": self.retries,
            "timeout": self.timeout,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "metadata": dict(self.metadata),
        }
