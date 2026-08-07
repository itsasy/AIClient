from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import Any


@dataclass(slots=True)
class ExecutionResult:
    """
    Resultado estándar producido por una ejecución.

    Representa la salida de:

    - AgentRuntime.
    - SkillRuntime.
    - ExecutionStep.
    - ExecutionEngine.

    No:

    - Ejecuta acciones.
    - Cambia estados del ExecutionPlan.
    - Gestiona contexto.
    - Decide reintentos.
    - Maneja lifecycle.
    """

    # ==================================================
    # Identity
    # ==================================================

    success: bool = False

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    # ==================================================
    # Output
    # ==================================================

    output: Any = None

    error: str | None = None

    error_type: str | None = None

    # ==================================================
    # Execution metadata
    # ==================================================

    execution_type: str | None = None

    executor: str | None = None

    unit_name: str | None = None

    step_id: str | None = None

    plan_id: str | None = None

    # ==================================================
    # Metrics
    # ==================================================

    duration_ms: float | None = None

    tokens_used: int | None = None

    retries: int = 0

    # ==================================================
    # Additional data
    # ==================================================

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    artifacts: list[Any] = field(
        default_factory=list,
    )

    warnings: list[str] = field(
        default_factory=list,
    )

    # ==================================================
    # Factory methods
    # ==================================================

    @classmethod
    def success_result(
        cls,
        output: Any = None,
        **kwargs: Any,
    ) -> "ExecutionResult":

        return cls(
            success=True,
            output=output,
            **kwargs,
        )

    @classmethod
    def failure_result(
        cls,
        error: str,
        error_type: str | None = None,
        **kwargs: Any,
    ) -> "ExecutionResult":

        return cls(
            success=False,
            error=error,
            error_type=error_type,
            **kwargs,
        )

    # ==================================================
    # State helpers
    # ==================================================

    def add_warning(
        self,
        warning: str,
    ) -> None:

        if warning:
            self.warnings.append(
                warning,
            )

    def add_artifact(
        self,
        artifact: Any,
    ) -> None:

        if artifact is not None:

            self.artifacts.append(
                artifact,
            )

    def is_successful(
        self,
    ) -> bool:

        return self.success and self.error is None

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "error_type": self.error_type,
            "execution_type": self.execution_type,
            "executor": self.executor,
            "unit_name": self.unit_name,
            "step_id": self.step_id,
            "plan_id": self.plan_id,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "retries": self.retries,
            "metadata": dict(self.metadata),
            "artifacts": list(self.artifacts),
            "warnings": list(self.warnings),
            "created_at": self.created_at.isoformat(),
        }
