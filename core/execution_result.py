from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from typing import Any


@dataclass
class ExecutionResult:
    """
    Resultado estándar de ejecución.

    Usado por:

    - AgentRuntime.
    - SkillRuntime.
    - ExecutionRuntime.
    - ExecutionEngine.

    Representa el resultado final
    de una unidad ejecutable.
    """

    success: bool

    output: Any = None

    error: str | None = None

    executor: str | None = None

    plan_id: str | None = None

    status: str = "completed"

    created_at: datetime = field(
        default_factory=lambda: datetime.now().astimezone(),
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    children: list["ExecutionResult"] = field(
        default_factory=list,
    )

    # ======================================================
    # Factory
    # ======================================================

    @classmethod
    def ok(
        cls,
        output: Any = None,
        executor: str | None = None,
        plan_id: str | None = None,
    ) -> "ExecutionResult":

        return cls(
            success=True,
            output=output,
            executor=executor,
            plan_id=plan_id,
            status="completed",
        )

    @classmethod
    def fail(
        cls,
        error: str,
        executor: str | None = None,
        plan_id: str | None = None,
    ) -> "ExecutionResult":

        return cls(
            success=False,
            error=error,
            executor=executor,
            plan_id=plan_id,
            status="failed",
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
            success=False,
            output=output,
            executor=executor,
            plan_id=plan_id,
            status="partial",
            children=children or [],
        )

    # ======================================================
    # Helpers
    # ======================================================

    def is_success(
        self,
    ) -> bool:

        return self.status == "completed" and self.success

    def is_failed(
        self,
    ) -> bool:

        return self.status == "failed"

    def add_child(
        self,
        result: "ExecutionResult",
    ) -> None:

        self.children.append(
            result,
        )

    def with_metadata(
        self,
        **values: Any,
    ) -> "ExecutionResult":

        self.metadata.update(
            values,
        )

        return self

    # ======================================================
    # Serialization
    # ======================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "success": self.success,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "executor": self.executor,
            "plan_id": self.plan_id,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
        }
