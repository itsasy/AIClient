from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class ExecutionResult:
    """
    Resultado producido durante o al finalizar una ejecución.

    Estados públicos finales:

        completed
        partial
        failed
        cancelled

    "retry" es un estado transitorio utilizado internamente por
    ExecutionEngine cuando una evaluación determina que la ejecución
    debe repetirse.

    Los reintentos no constituyen un estado final de ejecución.
    """

    VALID_STATUSES = frozenset(
        {
            "completed",
            "partial",
            "failed",
            "cancelled",
            "retry",
        }
    )

    FINAL_STATUSES = frozenset(
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
        if not isinstance(self.plan_id, str) or not self.plan_id.strip():
            raise ValueError("ExecutionResult requiere plan_id.")

        self.plan_id = self.plan_id.strip()

        if not isinstance(self.status, str):
            raise ValueError("ExecutionResult.status debe ser un string.")

        self.status = self.status.strip().lower()

        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Estado de ejecución inválido: {self.status}. "
                f"Estados permitidos: "
                f"{sorted(self.VALID_STATUSES)}"
            )

        if isinstance(self.retries, bool) or not isinstance(self.retries, int):
            raise ValueError("ExecutionResult.retries debe ser un entero.")

        if self.retries < 0:
            raise ValueError("ExecutionResult.retries no puede ser negativo.")

        if not isinstance(self.metadata, dict):
            raise ValueError("ExecutionResult.metadata debe ser un diccionario.")

        if self.error is not None:
            self.error = str(self.error)

        if self.executor is not None:
            self.executor = str(self.executor)

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
            metadata=dict(metadata or {}),
        )

    @classmethod
    def partial(
        cls,
        plan_id: str,
        result: Any = None,
        error: str | None = None,
        executor: str | None = None,
        retries: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        now = datetime.now(timezone.utc)

        return cls(
            plan_id=plan_id,
            status="partial",
            result=result,
            error=error,
            executor=executor,
            retries=retries,
            started_at=now,
            finished_at=now,
            metadata=dict(metadata or {}),
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
            metadata=dict(metadata or {}),
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
            metadata=dict(metadata or {}),
        )

    @classmethod
    def retry(
        cls,
        plan_id: str,
        error: str | None = None,
        retries: int = 0,
        executor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        now = datetime.now(timezone.utc)

        return cls(
            plan_id=plan_id,
            status="retry",
            error=error,
            executor=executor,
            retries=retries,
            started_at=now,
            finished_at=now,
            metadata=dict(metadata or {}),
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
    def is_retry(self) -> bool:
        return self.status == "retry"

    @property
    def is_terminal(self) -> bool:
        return self.status in self.FINAL_STATUSES

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

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ExecutionResult:

        if not isinstance(data, dict):
            raise ValueError("ExecutionResult.from_dict requiere un diccionario.")

        return cls(
            plan_id=data.get("plan_id", ""),
            status=data.get("status", ""),
            result=data.get("result"),
            error=data.get("error"),
            executor=data.get("executor"),
            retries=data.get("retries", 0),
            started_at=(
                datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
            ),
            finished_at=(
                datetime.fromisoformat(data["finished_at"]) if data.get("finished_at") else None
            ),
            metadata=data.get("metadata", {}),
        )
