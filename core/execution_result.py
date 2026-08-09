from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ExecutionResult:
    """
    Resultado final producido por ExecutionEngine.

    Representa el resultado de una ejecución completa.

    Estados finales:

        completed
        partial
        failed
        cancelled

    Los reintentos pertenecen al mecanismo de ejecución,
    no al estado final del resultado.
    """

    VALID_STATUSES = frozenset(
        {
            "completed",
            "partial",
            "failed",
            "cancelled",
        }
    )

    plan_id: str

    status: str

    result: Any = None

    error: str | None = None

    executor: str | None = None

    retries: int = 0

    started_at: datetime | None = None

    finished_at: datetime | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:

        self.status = self.status.strip().lower()

        if not self.plan_id:
            raise ValueError("ExecutionResult requiere plan_id.")

        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Estado de ejecución inválido: {self.status}. "
                f"Estados permitidos: "
                f"{sorted(self.VALID_STATUSES)}"
            )

        if self.retries < 0:
            raise ValueError("ExecutionResult.retries no puede ser negativo.")

    # =========================================================
    # Factory methods
    # =========================================================

    @classmethod
    def success(
        cls,
        plan_id: str,
        result: Any = None,
        executor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        now = datetime.now(timezone.utc)

        return cls(
            plan_id=plan_id,
            status="completed",
            result=result,
            executor=executor,
            started_at=now,
            finished_at=now,
            metadata=metadata or {},
        )

    @classmethod
    def partial(
        cls,
        plan_id: str,
        result: Any = None,
        error: str | None = None,
        executor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        now = datetime.now(timezone.utc)

        return cls(
            plan_id=plan_id,
            status="partial",
            result=result,
            error=error,
            executor=executor,
            started_at=now,
            finished_at=now,
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        plan_id: str,
        error: str,
        executor: str | None = None,
        retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        now = datetime.now(timezone.utc)

        return cls(
            plan_id=plan_id,
            status="failed",
            error=error,
            executor=executor,
            retries=retries,
            started_at=now,
            finished_at=now,
            metadata=metadata or {},
        )

    @classmethod
    def cancelled(
        cls,
        plan_id: str,
        executor: str | None = None,
        retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        now = datetime.now(timezone.utc)

        return cls(
            plan_id=plan_id,
            status="cancelled",
            executor=executor,
            retries=retries,
            started_at=now,
            finished_at=now,
            metadata=metadata or {},
        )

    # =========================================================
    # State
    # =========================================================

    @property
    def is_success(self) -> bool:
        return self.status == "completed"

    @property
    def is_failure(self) -> bool:
        return self.status == "failed"

    @property
    def is_partial(self) -> bool:
        return self.status == "partial"

    @property
    def is_cancelled(self) -> bool:
        return self.status == "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self.status in self.VALID_STATUSES

    # =========================================================
    # Serialization
    # =========================================================

    def to_dict(self) -> dict[str, Any]:

        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "executor": self.executor,
            "retries": self.retries,
            "started_at": (self.started_at.isoformat() if self.started_at else None),
            "finished_at": (self.finished_at.isoformat() if self.finished_at else None),
            "metadata": dict(self.metadata),
        }
