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

    ExecutionPlan es la fuente de verdad de una ejecución.

    El plan es construido por Planning y consumido por Runtime.
    Runtime no debe reinterpretar la intención original.
    """

    VALID_EXECUTION_MODES = frozenset(
        {
            "single",
            "multi_step",
        }
    )

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

    VALID_UNIT_TYPES = ExecutionStep.VALID_UNIT_TYPES

    VALID_GOVERNANCE_MODES = frozenset(
        {
            "safe",
            "powerful",
        }
    )

    # =========================================================
    # Identidad
    # =========================================================

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    status: str = "pending"

    # =========================================================
    # Intención
    # =========================================================

    original_task: str = ""

    intent: str | None = None

    intent_category: str | None = None

    objective: str | None = None

    # =========================================================
    # Ejecución
    # =========================================================

    execution_mode: str = "single"

    execution_unit_type: str | None = None

    execution_unit: str | None = None

    # =========================================================
    # Parámetros
    # =========================================================

    params: dict[str, Any] = field(default_factory=dict)

    constraints: list[str] = field(default_factory=list)

    # =========================================================
    # Context requirements
    # =========================================================

    context_requirements: dict[str, bool] = field(
        default_factory=lambda: {
            "project": False,
            "engram": False,
            "obsidian": False,
            "gentleman": False,
            "standards": False,
            "documents": False,
            "memory": False,
        }
    )

    # =========================================================
    # Governance
    # =========================================================

    governance: dict[str, Any] = field(
        default_factory=lambda: {
            "mode": "safe",
            "allow_shell": False,
            "allow_network": False,
            "allow_write": False,
            "allow_sudo": False,
        }
    )

    # =========================================================
    # Execution policy
    # =========================================================

    execution_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "autonomous": False,
            "max_retries": 2,
            "requires_approval": False,
            "stop_on_error": True,
            "timeout": 300,
        }
    )

    # =========================================================
    # Steps
    # =========================================================

    steps: list[ExecutionStep] = field(default_factory=list)

    # =========================================================
    # Runtime context
    # =========================================================

    loaded_context: dict[str, Any] = field(default_factory=dict)

    execution_context: dict[str, Any] = field(default_factory=dict)

    # =========================================================
    # Metadata
    # =========================================================

    metadata: dict[str, Any] = field(default_factory=dict)

    # =========================================================
    # Normalization
    # =========================================================

    @classmethod
    def normalize_unit_type(
        cls,
        unit_type: str | None,
    ) -> str | None:

        if unit_type is None:
            return None

        value = unit_type.lower().strip().replace("-", "_").replace(" ", "_")

        if value not in cls.VALID_UNIT_TYPES:
            raise ValueError(
                f"Tipo de unidad inválido: {value}. "
                f"Tipos permitidos: {sorted(cls.VALID_UNIT_TYPES)}"
            )

        return value

    @classmethod
    def normalize_execution_mode(
        cls,
        mode: str | None,
    ) -> str:

        if mode is None:
            return "single"

        value = mode.lower().strip().replace("-", "_").replace(" ", "_")

        if value not in cls.VALID_EXECUTION_MODES:
            raise ValueError(
                f"Modo de ejecución inválido: {value}. "
                f"Modos permitidos: {sorted(cls.VALID_EXECUTION_MODES)}"
            )

        return value

    # =========================================================
    # Lifecycle
    # =========================================================

    def __post_init__(self) -> None:

        self.original_task = self.original_task.strip()

        self.execution_mode = self.normalize_execution_mode(self.execution_mode)

        if self.execution_unit_type is not None:
            self.execution_unit_type = self.normalize_unit_type(self.execution_unit_type)

        if self.execution_unit is not None:
            self.execution_unit = self.execution_unit.strip()

        if self.execution_unit_type is not None:
            if not self.execution_unit:
                raise ValueError(
                    "execution_unit es obligatorio cuando " "execution_unit_type está definido."
                )

        if self.status not in self.VALID_STATUSES:
            raise ValueError(
                f"Estado de plan inválido: {self.status}. "
                f"Estados permitidos: {sorted(self.VALID_STATUSES)}"
            )

        governance_mode = self.governance.get(
            "mode",
            "safe",
        )

        governance_mode = str(governance_mode).lower().strip()

        if governance_mode not in self.VALID_GOVERNANCE_MODES:
            raise ValueError(
                f"Modo de governance inválido: {governance_mode}. "
                f"Modos permitidos: {sorted(self.VALID_GOVERNANCE_MODES)}"
            )

        self.governance["mode"] = governance_mode

        max_retries = self.execution_policy.get(
            "max_retries",
            2,
        )

        if not isinstance(max_retries, int) or max_retries < 0:
            raise ValueError(
                "execution_policy.max_retries debe ser " "un entero mayor o igual a cero."
            )

        timeout = self.execution_policy.get(
            "timeout",
            300,
        )

        if not isinstance(timeout, int) or timeout <= 0:
            raise ValueError("execution_policy.timeout debe ser " "un entero mayor que cero.")

    # =========================================================
    # Context
    # =========================================================

    def requires_context(
        self,
        provider: str,
    ) -> bool:

        return self.context_requirements.get(
            provider,
            False,
        )

    def set_context_requirement(
        self,
        provider: str,
        required: bool,
    ) -> None:

        self.context_requirements[provider] = required

    # =========================================================
    # Governance
    # =========================================================

    def is_safe_mode(self) -> bool:
        return (
            self.governance.get(
                "mode",
                "safe",
            )
            == "safe"
        )

    def is_powerful_mode(self) -> bool:
        return (
            self.governance.get(
                "mode",
                "safe",
            )
            == "powerful"
        )

    def allows_shell(self) -> bool:
        return self.governance.get(
            "allow_shell",
            False,
        )

    def allows_network(self) -> bool:
        return self.governance.get(
            "allow_network",
            False,
        )

    def allows_write(self) -> bool:
        return self.governance.get(
            "allow_write",
            False,
        )

    def allows_sudo(self) -> bool:
        return self.governance.get(
            "allow_sudo",
            False,
        )

    # =========================================================
    # Execution policy
    # =========================================================

    def is_autonomous(self) -> bool:
        return self.execution_policy.get(
            "autonomous",
            False,
        )

    def get_max_retries(self) -> int:
        return self.execution_policy.get(
            "max_retries",
            2,
        )

    def requires_approval(self) -> bool:
        return self.execution_policy.get(
            "requires_approval",
            False,
        )

    def should_stop_on_error(self) -> bool:
        return self.execution_policy.get(
            "stop_on_error",
            True,
        )

    def get_timeout(self) -> int:
        return self.execution_policy.get(
            "timeout",
            300,
        )

    # =========================================================
    # Steps
    # =========================================================

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
            unit_type=self.normalize_unit_type(unit_type),
            unit_name=unit_name,
            params=params or {},
            expected_output=expected_output,
            retries=retries,
            timeout=timeout,
            metadata=metadata or {},
        )

        self.steps.append(step)

        return step

    def has_steps(self) -> bool:
        return bool(self.steps)

    def is_multi_step(self) -> bool:
        return self.execution_mode == "multi_step"

    # =========================================================
    # Validation
    # =========================================================

    def validate(self) -> list[str]:

        errors: list[str] = []

        if not self.original_task:
            errors.append("ExecutionPlan requiere original_task.")

        if not self.intent:
            errors.append("ExecutionPlan requiere intent.")

        if self.execution_mode == "single":

            if not self.execution_unit_type:
                errors.append("Modo single requiere execution_unit_type.")

            if not self.execution_unit:
                errors.append("Modo single requiere execution_unit.")

            if self.steps:
                errors.append("Modo single no permite steps.")

        elif self.execution_mode == "multi_step":

            if not self.steps and not self.execution_unit:
                errors.append(
                    "Modo multi_step requiere al menos " "un step o una unidad ejecutable."
                )

        step_ids = {step.id for step in self.steps}

        for step in self.steps:

            for dependency in step.depends_on:

                if dependency not in step_ids:
                    errors.append(f"Step {step.id} depende de " f"{dependency}, que no existe.")

        return errors

    def is_valid(self) -> bool:
        return not self.validate()

    # =========================================================
    # Status
    # =========================================================

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

    # =========================================================
    # Serialization
    # =========================================================

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
            "context_requirements": dict(self.context_requirements),
            "governance": dict(self.governance),
            "execution_policy": dict(self.execution_policy),
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
            f"unit={self.execution_unit_type}:"
            f"{self.execution_unit}, "
            f"steps={len(self.steps)})>"
        )
