from __future__ import annotations

from dataclasses import dataclass, field

from datetime import datetime, timezone

from typing import Any

VALID_RESULT_STATUS = {
    "completed",
    "partial",
    "failed",
}


@dataclass(slots=True)
class ExecutionResult:
    """
    Resultado estándar de ejecución.

    Representa:

    - Estado final.
    - Resultado producido.
    - Errores.
    - Metadata de ejecución.

    No:

    - Ejecuta.
    - Decide.
    - Modifica planes.
    """

    status: str

    result: Any = None

    error: str | None = None

    executor: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )

    # ==================================================
    # Validation
    # ==================================================

    def __post_init__(
        self,
    ) -> None:

        self.status = self.normalize_status(
            self.status,
        )

        if self.status not in VALID_RESULT_STATUS:

            raise ValueError(f"Estado de resultado inválido: {self.status}")

    # ==================================================
    # Factories
    # ==================================================

    @classmethod
    def success(
        cls,
        result: Any = None,
        executor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ExecutionResult":

        return cls(
            status="completed",
            result=result,
            executor=executor,
            metadata=metadata or {},
        )

    @classmethod
    def partial(
        cls,
        result: Any = None,
        error: str | None = None,
        executor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ExecutionResult":

        return cls(
            status="partial",
            result=result,
            error=error,
            executor=executor,
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        error: str,
        executor: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "ExecutionResult":

        return cls(
            status="failed",
            error=error,
            executor=executor,
            metadata=metadata or {},
        )

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def normalize_status(
        status: str,
    ) -> str:

        if not status:

            return ""

        return (
            status.lower()
            .strip()
            .replace(
                "-",
                "_",
            )
            .replace(
                " ",
                "_",
            )
        )

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "executor": self.executor,
            "metadata": dict(self.metadata),
            "created_at": self.created_at.isoformat(),
        }

    def is_success(
        self,
    ) -> bool:

        return self.status == "completed"

    def is_failure(
        self,
    ) -> bool:

        return self.status == "failed"
