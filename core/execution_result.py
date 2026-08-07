from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import Any

VALID_RESULT_STATUS = {
    "completed",
    "failed",
    "partial",
}


@dataclass(slots=True)
class ExecutionResult:
    """
    Contrato único de resultado de ejecución.

    Representa:

    - Resultado exitoso.
    - Resultado fallido.
    - Resultado parcial.

    Puede contener resultados hijos
    para ejecuciones multi-step o paralelas.

    No:

    - Ejecuta lógica.
    - Modifica planes.
    - Decide retries.
    """

    status: str

    output: Any = None

    error: str | None = None

    executor: str | None = None

    plan_id: str | None = None

    trace_id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    children: list["ExecutionResult"] = field(
        default_factory=list,
    )

    def __post_init__(self) -> None:

        if self.status not in VALID_RESULT_STATUS:

            raise ValueError(f"Estado inválido: {self.status}")

    # ==================================================
    # Factory methods
    # ==================================================

    @classmethod
    def ok(
        cls,
        output: Any = None,
        executor: str | None = None,
        plan_id: str | None = None,
    ) -> "ExecutionResult":

        return cls(
            status="completed",
            output=output,
            executor=executor,
            plan_id=plan_id,
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

    # ==================================================
    # State
    # ==================================================

    @property
    def success(
        self,
    ) -> bool:

        return self.status in {
            "completed",
            "partial",
        }

    def is_success(
        self,
    ) -> bool:

        return self.success

    def is_failed(
        self,
    ) -> bool:

        return self.status == "failed"

    # ==================================================
    # Children
    # ==================================================

    def add_child(
        self,
        result: "ExecutionResult",
    ) -> None:

        self.children.append(
            result,
        )

    # ==================================================
    # Metadata
    # ==================================================

    def with_metadata(
        self,
        values: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "ExecutionResult":

        if values:
            self.metadata.update(values)

        if kwargs:
            self.metadata.update(kwargs)

        return self

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "status": self.status,
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "executor": self.executor,
            "plan_id": self.plan_id,
            "trace_id": self.trace_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
        }
