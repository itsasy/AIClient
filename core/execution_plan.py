from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep


@dataclass(slots=True)
class ExecutionPlan:
    """
    Contrato central de ejecución de AIClient.
    """

    VALID_EXECUTION_MODES = frozenset({"single", "multi_step"})
    VALID_STATUSES = frozenset(
        {
            "pending",
            "planned",
            "validated",
            "running",
            "completed",
            "partial",
            "failed",
            "cancelled",
        }
    )

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"

    original_task: str = ""
    intent: str | None = None
    intent_category: str | None = None
    objective: str | None = None

    execution_mode: str = "single"
    execution_unit_type: str | None = None
    execution_unit: str | None = None

    params: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    context_requirements: list[str] = field(default_factory=list)
    steps: list[ExecutionStep] = field(default_factory=list)

    max_retries: int = 2
    stop_on_error: bool = True
    loaded_context: dict[str, Any] = field(default_factory=dict)
    execution_context: dict[str, Any] = field(default_factory=dict)

    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.original_task = self.original_task.strip()
        self.execution_mode = self.execution_mode.strip().lower()

        if self.execution_mode not in self.VALID_EXECUTION_MODES:
            raise ValueError(
                f"Modo de ejecución inválido: {self.execution_mode}. "
                f"Modos permitidos: {sorted(self.VALID_EXECUTION_MODES)}"
            )

        if self.execution_unit_type is not None:
            self.execution_unit_type = self.execution_unit_type.strip().lower()

        if self.execution_unit is not None:
            self.execution_unit = self.execution_unit.strip()

        if self.execution_unit_type is not None:
            if self.execution_unit_type not in ExecutionStep.VALID_UNIT_TYPES:
                raise ValueError(
                    f"Tipo de unidad inválido: {self.execution_unit_type}. "
                    f"Tipos permitidos: {sorted(ExecutionStep.VALID_UNIT_TYPES)}"
                )
            if not self.execution_unit:
                raise ValueError(
                    "execution_unit es obligatorio cuando execution_unit_type está definido."
                )

        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Estado de plan inválido: {self.status}. "
                f"Estados permitidos: {sorted(self.VALID_STATUSES)}"
            )

    def add_step(
        self,
        description: str,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
        expected_output: str | None = None,
        retries: int = 0,
        timeout: int = 120,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionStep:
        step = ExecutionStep(
            description=description,
            unit_type=unit_type,
            unit_name=unit_name,
            params=params or {},
            expected_output=expected_output,
            retries=retries,
            timeout=timeout,
            metadata=metadata or {},
        )
        self.steps.append(step)
        return step

    def validate(self) -> list[str]:
        errors = []

        if not self.original_task:
            errors.append("ExecutionPlan requiere original_task.")

        if not self.intent:
            errors.append("ExecutionPlan requiere intent.")

        if self.execution_mode == "single":
            if not self.execution_unit_type or not self.execution_unit:
                errors.append("Modo single requiere execution_unit_type y execution_unit.")
            if self.steps:
                errors.append("Modo single no permite steps.")
        elif self.execution_mode == "multi_step":
            if not self.steps and not self.execution_unit:
                errors.append("Modo multi_step requiere al menos un step o una unidad ejecutable.")

        step_ids = {step.id for step in self.steps}
        for step in self.steps:
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(f"Step {step.id} depende de {dep}, que no existe.")

        return errors

    def is_valid(self) -> bool:
        return not bool(self.validate())

    def mark_planned(self) -> None:
        self.status = "planned"

    def mark_validated(self) -> None:
        self.status = "validated"

    def mark_running(self) -> None:
        self.status = "running"

    def mark_completed(self) -> None:
        self.status = "completed"

    def mark_partial(self) -> None:
        self.status = "partial"

    def mark_failed(self) -> None:
        self.status = "failed"

    def mark_cancelled(self) -> None:
        self.status = "cancelled"

    def has_steps(self) -> bool:
        return bool(self.steps)

    def is_multi_step(self) -> bool:
        return self.execution_mode == "multi_step"

    def requires_context(self, provider: str) -> bool:
        return provider in self.context_requirements

    def uses_unit(self, unit_type: str, unit_name: str) -> bool:
        if self.execution_unit_type == unit_type and self.execution_unit == unit_name:
            return True
        return any(
            step.unit_type == unit_type and step.unit_name == unit_name for step in self.steps
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "original_task": self.original_task,
            "intent": self.intent,
            "intent_category": self.intent_category,
            "objective": self.objective,
            "execution_mode": self.execution_mode,
            "execution_unit_type": self.execution_unit_type,
            "execution_unit": self.execution_unit,
            "params": dict(self.params),
            "constraints": list(self.constraints),
            "context_requirements": list(self.context_requirements),
            "max_retries": self.max_retries,
            "stop_on_error": self.stop_on_error,
            "loaded_context": dict(self.loaded_context),
            "execution_context": dict(self.execution_context),
            "metadata": dict(self.metadata),
            "steps": [step.to_dict() for step in self.steps],
        }

    def __repr__(self) -> str:
        return (
            f"<ExecutionPlan("
            f"id={self.id}, "
            f"status={self.status}, "
            f"intent={self.intent}, "
            f"unit={self.execution_unit_type}:{self.execution_unit}, "
            f"steps={len(self.steps)})>"
        )
