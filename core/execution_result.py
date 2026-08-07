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
    Resultado estándar del sistema de ejecución.

    Representa la salida de:

    - AgentRuntime.
    - SkillRuntime.
    - ExecutionRuntime.
    - ExecutionEngine.
    - Pipeline.

    Responsabilidades:

    - Transportar resultado.
    - Transportar errores.
    - Mantener metadata.
    - Mantener resultados hijos.

    No:

    - Ejecuta lógica.
    - Decide estados.
    - Gestiona retries.
    """

    status: str

    output: Any = None

    error: str | None = None

    executor: str | None = None

    plan_id: str | None = None

    children: list["ExecutionResult"] = field(
        default_factory=list,
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(
            timezone.utc,
        ),
    )

    # ==================================================
    # Factory methods
    # ==================================================

    @classmethod
    def ok(
        cls,
        output: Any = None,
        executor: str | None = None,
        plan_id: str | None = None,
        children: list["ExecutionResult"] | None = None,
    ) -> "ExecutionResult":

        return cls(
            status="completed",
            output=output,
            executor=executor,
            plan_id=plan_id,
            children=children or [],
        )

    @classmethod
    def partial(
        cls,
        output: Any = None,
        executor: str | None = None,
        plan_id: str | None = None,
        children: list["ExecutionResult"] | None = None,
    ) -> "ExecutionResult":

        return cls(
            status="partial",
            output=output,
            executor=executor,
            plan_id=plan_id,
            children=children or [],
        )

    @classmethod
    def fail(
        cls,
        error: str,
        executor: str | None = None,
        plan_id: str | None = None,
    ) -> "ExecutionResult":

        return cls(
            status="failed",
            error=error,
            executor=executor,
            plan_id=plan_id,
        )

    # ==================================================
    # Lifecycle
    # ==================================================

    def __post_init__(
        self,
    ) -> None:

        if self.status not in VALID_RESULT_STATUS:

            raise ValueError(
                f"Estado inválido: {self.status}",
            )

    # ==================================================
    # Helpers
    # ==================================================

    def is_success(
        self,
    ) -> bool:

        return self.status == "completed"

    def is_partial(
        self,
    ) -> bool:

        return self.status == "partial"

    def is_failed(
        self,
    ) -> bool:

        return self.status == "failed"

    def with_metadata(
        self,
        **metadata: Any,
    ) -> "ExecutionResult":

        self.metadata.update(
            metadata,
        )

        return self

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "executor": self.executor,
            "plan_id": self.plan_id,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata.copy(),
            "created_at": self.created_at.isoformat(),
        }
