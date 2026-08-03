from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExecutionResult:
    """
    Resultado estándar de ejecución.

    Usado por:
    - AgentRuntime
    - SkillRuntime
    - ExecutionRuntime
    - ExecutionEngine
    """

    success: bool

    output: Any = None

    error: str | None = None

    executor: str | None = None

    plan_id: str | None = None

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    @classmethod
    def ok(
        cls,
        output: Any,
        executor: str | None = None,
        plan_id: str | None = None,
    ):

        return cls(
            success=True,
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
    ):

        return cls(
            success=False,
            error=error,
            executor=executor,
            plan_id=plan_id,
        )

    def to_dict(self) -> dict[str, Any]:

        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "executor": self.executor,
            "plan_id": self.plan_id,
            "metadata": self.metadata,
        }
