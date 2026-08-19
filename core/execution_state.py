from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ExecutionState:
    """
    Estado runtime de una ejecución.
    Separado de ExecutionPlan (que solo contiene planificación).
    """

    plan_id: str
    status: str = (
        "created"  # created | validated | running | completed | partial | failed | cancelled
    )

    result: Any = None
    error: str | None = None

    loaded_context: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)

    started_at: datetime | None = None
    finished_at: datetime | None = None

    retries: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def mark_validated(self) -> None:
        self.status = "validated"

    def mark_running(self) -> None:
        self.status = "running"
        if self.started_at is None:
            self.started_at = datetime.now(timezone.utc)

    def mark_completed(self, result: Any = None) -> None:
        self.status = "completed"
        self.result = result
        self.error = None
        self.finished_at = datetime.now(timezone.utc)

    def mark_partial(self, result: Any = None, error: str | None = None) -> None:
        self.status = "partial"
        self.result = result
        self.error = error
        self.finished_at = datetime.now(timezone.utc)

    def mark_failed(self, error: str) -> None:
        self.status = "failed"
        self.error = str(error)
        self.finished_at = datetime.now(timezone.utc)

    def mark_cancelled(self) -> None:
        self.status = "cancelled"
        self.finished_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "retries": self.retries,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "metadata": dict(self.metadata),
        }
