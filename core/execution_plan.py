from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from core.execution_step import ExecutionStep
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout


from core.plan_mixins.validation_mixin import PlanValidationMixin
from core.plan_mixins.lifecycle_mixin import PlanLifecycleMixin
from core.plan_mixins.governance_mixin import PlanGovernanceMixin
from core.plan_mixins.step_mixin import PlanStepMixin
from core.plan_mixins.context_mixin import PlanContextMixin
from core.plan_mixins.serialization_mixin import PlanSerializationMixin

@dataclass(slots=True)
class ExecutionPlan(
    PlanValidationMixin,
    PlanLifecycleMixin,
    PlanGovernanceMixin,
    PlanStepMixin,
    PlanContextMixin,
    PlanSerializationMixin,
):
    """
    Contrato central de ejecución de AIClient.

    ExecutionPlan es la fuente de verdad de una ejecución.

    El plan es construido por Planning y consumido por Runtime.

    Responsabilidades:

        - representar la intención que originó la ejecución;
        - definir el objetivo;
        - definir la modalidad de ejecución;
        - definir la unidad ejecutable o los steps;
        - definir dependencias;
        - declarar requisitos de contexto;
        - declarar governance/policy;
        - conservar metadata de planificación;
        - controlar el lifecycle del plan;
        - serializar/deserializar el contrato.

    No:

        - ejecuta Agents;
        - ejecuta Skills;
        - descubre unidades;
        - interpreta lenguaje natural;
        - resuelve proveedores LLM;
        - carga contexto por sí mismo.
    """

    # =========================================================
    # Constants
    # =========================================================

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
            "paused",
            "not_available",
        }
    )

    VALID_UNIT_TYPES = ExecutionStep.VALID_UNIT_TYPES

    VALID_GOVERNANCE_MODES = frozenset(
        {
            "safe",
            "powerful",
        }
    )

    DEFAULT_CONTEXT_REQUIREMENTS = {
        "project": False,
        "engram": False,
        "memory": False,
        "obsidian": False,
        "gentleman": False,
        "standards": False,
        "documents": False,
        "spec": False,
        "swarmforge": False,
    }

    DEFAULT_GOVERNANCE = {
        "mode": "safe",
        "allow_shell": False,
        "allow_network": False,
        "allow_write": False,
        "allow_sudo": False,
    }

    DEFAULT_EXECUTION_POLICY = {
        "autonomous": False,
        "max_retries": 2,
        "requires_approval": False,
        "stop_on_error": True,
        "timeout": 300,
    }

    # =========================================================
    # Identity
    # =========================================================

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    status: str = "pending"

    # =========================================================
    # Intent
    # =========================================================

    original_task: str = ""

    intent: str | None = None

    intent_category: str | None = None

    objective: str | None = None

    # =========================================================
    # Execution
    # =========================================================

    execution_mode: str = "single"

    execution_unit_type: str | None = None

    execution_unit: str | None = None

    # =========================================================
    # Parameters
    # =========================================================

    params: dict[str, Any] = field(default_factory=dict)

    constraints: list[str] = field(default_factory=list)

    # =========================================================
    # Context requirements
    # =========================================================

    context_requirements: dict[str, bool] = field(
        default_factory=lambda: dict(ExecutionPlan.DEFAULT_CONTEXT_REQUIREMENTS)
    )

    # =========================================================
    # Governance
    # =========================================================

    governance: dict[str, Any] = field(
        default_factory=lambda: dict(ExecutionPlan.DEFAULT_GOVERNANCE)
    )

    # =========================================================
    # Execution policy
    # =========================================================

    execution_policy: dict[str, Any] = field(
        default_factory=lambda: dict(ExecutionPlan.DEFAULT_EXECUTION_POLICY)
    )

    # =========================================================
    # Steps
    # =========================================================

    steps: list[ExecutionStep] = field(default_factory=list)

    # =========================================================
    # Runtime
    # =========================================================

    loaded_context: dict[str, Any] = field(default_factory=dict)

    execution_context: dict[str, Any] = field(default_factory=dict)

    result: Any = None

    error: str | None = None

    # =========================================================
    # Metadata
    # =========================================================

    metadata: dict[str, Any] = field(default_factory=dict)

    # =========================================================
    # Initialization
    # =========================================================

    def __post_init__(self) -> None:
        self.original_task = self._normalize_text(self.original_task)

        self.execution_mode = self.normalize_execution_mode(self.execution_mode)

        self.status = self.normalize_status(self.status)

        if self.execution_unit_type is not None:
            self.execution_unit_type = self.normalize_unit_type(self.execution_unit_type)

        if self.execution_unit is not None:
            self.execution_unit = self.execution_unit.strip()

            if not self.execution_unit:
                self.execution_unit = None

        self.intent = self._normalize_optional_text(self.intent)

        self.intent_category = self._normalize_optional_text(self.intent_category)

        self.objective = self._normalize_optional_text(self.objective)

        self._validate_containers()
        self._normalize_context_requirements()
        self._normalize_governance()
        self._normalize_execution_policy()

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        if not isinstance(value, str):
            raise ValueError("El valor debe ser un string.")

        return value.strip()

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not isinstance(value, str):
            raise ValueError("El valor debe ser un string o None.")

        value = value.strip()

        return value or None

    @classmethod
    def normalize_unit_type(
        cls,
        unit_type: str | None,
    ) -> str | None:
        if unit_type is None:
            return None

        if not isinstance(unit_type, str):
            raise ValueError("execution_unit_type debe ser un string o None.")

        value = unit_type.lower().strip().replace("-", "_").replace(" ", "_")

        if value not in cls.VALID_UNIT_TYPES:
            raise ValueError(
                f"Tipo de unidad inválido: {value}. "
                f"Tipos permitidos: "
                f"{sorted(cls.VALID_UNIT_TYPES)}"
            )

        return value

    @classmethod
    def normalize_execution_mode(
        cls,
        mode: str | None,
    ) -> str:
        if mode is None:
            return "single"

        if not isinstance(mode, str):
            raise ValueError("execution_mode debe ser un string.")

        value = mode.lower().strip().replace("-", "_").replace(" ", "_")

        if value not in cls.VALID_EXECUTION_MODES:
            raise ValueError(
                f"Modo de ejecución inválido: {value}. "
                f"Modos permitidos: "
                f"{sorted(cls.VALID_EXECUTION_MODES)}"
            )

        return value

    @classmethod
    def normalize_status(
        cls,
        status: str,
    ) -> str:
        if not isinstance(status, str):
            raise ValueError("ExecutionPlan.status debe ser un string.")

        value = status.lower().strip()

        if value not in cls.VALID_STATUSES:
            raise ValueError(
                f"Estado de plan inválido: {value}. "
                f"Estados permitidos: "
                f"{sorted(cls.VALID_STATUSES)}"
            )

        return value

    def __repr__(self) -> str:
        return (
            "<ExecutionPlan("
            f"id={self.id}, "
            f"status={self.status}, "
            f"intent={self.intent}, "
            f"mode={self.execution_mode}, "
            f"unit={self.execution_unit_type}:"
            f"{self.execution_unit}, "
            f"steps={len(self.steps)}"
            ")>"
        )

