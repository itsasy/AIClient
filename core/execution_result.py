from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from typing import Any

VALID_RESULT_STATUS = {
    "completed",
    "failed",
    "partial",
}


@dataclass
class ExecutionResult:

    success: bool

    output: Any = None

    error: str | None = None

    executor: str | None = None

    plan_id: str | None = None

    status: str = "completed"

    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    metadata: dict[str, Any] = field(default_factory=dict)

    children: list["ExecutionResult"] = field(default_factory=list)

    def __post_init__(self):

        if self.status not in VALID_RESULT_STATUS:

            raise ValueError(f"Estado inválido: {self.status}")

    @classmethod
    def ok(
        cls,
        output=None,
        executor=None,
        plan_id=None,
    ):

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
        error,
        executor=None,
        plan_id=None,
    ):

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
        output=None,
        executor=None,
        plan_id=None,
        children=None,
    ):

        return cls(
            success=True,
            output=output,
            executor=executor,
            plan_id=plan_id,
            status="partial",
            children=children or [],
        )

    def is_success(self):

        return self.success and self.status in {
            "completed",
            "partial",
        }

    def is_failed(self):

        return self.status == "failed"

    def add_child(
        self,
        result: "ExecutionResult",
    ):

        self.children.append(result)

    def with_metadata(
        self,
        **values,
    ):

        self.metadata.update(values)

        return self

    def merge_metadata(
        self,
        values: dict[str, Any],
    ):

        self.metadata.update(values)

        return self

    def to_dict(self):

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
