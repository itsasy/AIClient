from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, ClassVar


@dataclass(slots=True)
class ExecutionResult:
    """
    Resultado producido durante o al finalizar una ejecución.

    Estados válidos:

        completed
        partial
        failed
        cancelled
        retry

    ``retry`` es exclusivamente transitorio.

    Un resultado público nunca debería terminar con status="retry":
    ExecutionEngine debe convertirlo en un estado terminal cuando
    los reintentos se agotan.

    ``retries`` representa la cantidad de reintentos ya realizados.
    """

    VALID_STATUSES: ClassVar[frozenset[str]] = frozenset(
        {
            "completed",
            "partial",
            "failed",
            "cancelled",
            "retry",
        }
    )

    FINAL_STATUSES: ClassVar[frozenset[str]] = frozenset(
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
        # ---------------------------------------------------------
        # plan_id
        # ---------------------------------------------------------

        if not isinstance(self.plan_id, str):
            raise ValueError(
                "ExecutionResult requiere plan_id.",
            )

        self.plan_id = self.plan_id.strip()

        if not self.plan_id:
            raise ValueError(
                "ExecutionResult requiere plan_id.",
            )

        # ---------------------------------------------------------
        # status
        # ---------------------------------------------------------

        if not isinstance(self.status, str):
            raise ValueError(
                "ExecutionResult.status debe ser un string.",
            )

        self.status = self.status.strip().lower()

        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Estado de ejecución inválido: {self.status}. "
                f"Estados permitidos: {sorted(self.VALID_STATUSES)}"
            )

        # ---------------------------------------------------------
        # retries
        # ---------------------------------------------------------

        if isinstance(self.retries, bool) or not isinstance(
            self.retries,
            int,
        ):
            raise ValueError(
                "ExecutionResult.retries debe ser un entero.",
            )

        if self.retries < 0:
            raise ValueError(
                "ExecutionResult.retries no puede ser negativo.",
            )

        # ---------------------------------------------------------
        # metadata
        # ---------------------------------------------------------

        if not isinstance(self.metadata, dict):
            raise ValueError(
                "ExecutionResult.metadata debe ser un diccionario.",
            )

        # Copia defensiva.
        self.metadata = dict(self.metadata)

        # ---------------------------------------------------------
        # optional values
        # ---------------------------------------------------------

        if self.error is not None:
            self.error = str(self.error).strip() or None

        if self.executor is not None:
            self.executor = str(self.executor).strip() or None

        # ---------------------------------------------------------
        # timestamps
        # ---------------------------------------------------------

        self.started_at = self._validate_datetime(
            self.started_at,
            "started_at",
        )

        self.finished_at = self._validate_datetime(
            self.finished_at,
            "finished_at",
        )

        if (
            self.started_at is not None
            and self.finished_at is not None
            and self.finished_at < self.started_at
        ):
            raise ValueError(
                "ExecutionResult.finished_at no puede ser anterior "
                "a started_at.",
            )

    # =========================================================
    # Validation helpers
    # =========================================================

    @staticmethod
    def _validate_datetime(
        value: datetime | None,
        field_name: str,
    ) -> datetime | None:
        if value is None:
            return None

        if not isinstance(value, datetime):
            raise ValueError(
                f"ExecutionResult.{field_name} debe ser datetime o None.",
            )

        return value

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    # =========================================================
    # Factories
    # =========================================================

    @classmethod
    def success(
        cls,
        plan_id: str,
        result: Any = None,
        executor: str | None = None,
        retries: int = 0,
        metadata: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ExecutionResult:
        now = cls._now()

        started = started_at or now
        finished = finished_at or now

        return cls(
            plan_id=plan_id,
            status="completed",
            result=result,
            executor=executor,
            retries=retries,
            started_at=started,
            finished_at=finished,
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
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ExecutionResult:
        now = cls._now()

        started = started_at or now
        finished = finished_at or now

        return cls(
            plan_id=plan_id,
            status="partial",
            result=result,
            error=error,
            executor=executor,
            retries=retries,
            started_at=started,
            finished_at=finished,
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
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ExecutionResult:
        if not isinstance(error, str) or not error.strip():
            raise ValueError(
                "ExecutionResult.fail requiere un error no vacío.",
            )

        now = cls._now()

        started = started_at or now
        finished = finished_at or now

        return cls(
            plan_id=plan_id,
            status="failed",
            error=error.strip(),
            executor=executor,
            retries=retries,
            started_at=started,
            finished_at=finished,
            metadata=dict(metadata or {}),
        )

    @classmethod
    def cancelled(
        cls,
        plan_id: str,
        executor: str | None = None,
        retries: int = 0,
        metadata: dict[str, Any] | None = None,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ExecutionResult:
        now = cls._now()

        started = started_at or now
        finished = finished_at or now

        return cls(
            plan_id=plan_id,
            status="cancelled",
            executor=executor,
            retries=retries,
            started_at=started,
            finished_at=finished,
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
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> ExecutionResult:
        """
        Resultado transitorio.

        ``finished_at`` se permite porque un retry también puede
        representar el cierre de un intento, pero ExecutionEngine
        reemplazará siempre el resultado por uno terminal antes
        de exponerlo públicamente.
        """

        now = cls._now()

        started = started_at or now

        return cls(
            plan_id=plan_id,
            status="retry",
            error=error,
            executor=executor,
            retries=retries,
            started_at=started,
            finished_at=finished_at,
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
    # Timestamp helpers
    # =========================================================

    def mark_started(
        self,
        started_at: datetime | None = None,
    ) -> None:
        value = started_at or self._now()

        if self.finished_at is not None and value > self.finished_at:
            raise ValueError(
                "started_at no puede ser posterior a finished_at.",
            )

        self.started_at = value

    def mark_finished(
        self,
        finished_at: datetime | None = None,
    ) -> None:
        value = finished_at or self._now()

        if self.started_at is not None and value < self.started_at:
            raise ValueError(
                "finished_at no puede ser anterior a started_at.",
            )

        self.finished_at = value

    def set_execution_window(
        self,
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
    ) -> None:
        if started_at is not None:
            self.mark_started(started_at)

        if finished_at is not None:
            self.mark_finished(finished_at)

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
            "started_at": (
                self.started_at.isoformat()
                if self.started_at
                else None
            ),
            "finished_at": (
                self.finished_at.isoformat()
                if self.finished_at
                else None
            ),
            "metadata": dict(self.metadata),
        }

    @staticmethod
    def _parse_datetime(
        value: Any,
        field_name: str,
    ) -> datetime | None:
        if value is None or value == "":
            return None

        if isinstance(value, datetime):
            return value

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} debe ser ISO datetime, datetime o None.",
            )

        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} no contiene un datetime ISO válido: "
                f"{value!r}",
            ) from exc

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> ExecutionResult:
        if not isinstance(data, dict):
            raise ValueError(
                "ExecutionResult.from_dict requiere un diccionario.",
            )

        return cls(
            plan_id=data.get("plan_id", ""),
            status=data.get("status", ""),
            result=data.get("result"),
            error=data.get("error"),
            executor=data.get("executor"),
            retries=data.get("retries", 0),
            started_at=cls._parse_datetime(
                data.get("started_at"),
                "started_at",
            ),
            finished_at=cls._parse_datetime(
                data.get("finished_at"),
                "finished_at",
            ),
            metadata=data.get("metadata", {}),
        )
