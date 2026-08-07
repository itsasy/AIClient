from __future__ import annotations

import copy
import uuid

from dataclasses import dataclass, field
from datetime import datetime, timezone

from typing import Any

from core.execution_step import ExecutionStep

VALID_STATUS = {
    "pending",
    "planned",
    "validated",
    "running",
    "partial",
    "completed",
    "failed",
    "learning",
    "cancelled",
}


VALID_TRANSITIONS = {
    "pending": {
        "planned",
        "cancelled",
    },
    "planned": {
        "validated",
        "cancelled",
    },
    "validated": {
        "running",
        "cancelled",
    },
    "running": {
        "partial",
        "completed",
        "failed",
        "cancelled",
    },
    "partial": {
        "running",
        "completed",
        "failed",
        "cancelled",
    },
    "completed": set(),
    "failed": {
        "running",
        "cancelled",
    },
    "learning": {
        "completed",
        "failed",
    },
    "cancelled": set(),
}


AVAILABLE_CONTEXT_PROVIDERS = {
    "project",
    "engram",
    "memory",
    "obsidian",
    "documents",
    "spec",
    "standards",
    "gentleman",
    "knowledge",
}


PROVIDER_ALIASES = {
    "project_context": "project",
    "projects": "project",
    "docs": "documents",
    "document": "documents",
    "document_context": "documents",
    "specification": "spec",
    "specifications": "spec",
    "standard": "standards",
}


UNIT_TYPES = {
    "agent",
    "skill",
}


UNIT_ALIASES = {
    "agents": "agent",
    "agent_runtime": "agent",
    "skills": "skill",
    "skill_runtime": "skill",
}


AVAILABLE_EXECUTION_MODES = {
    "single",
    "multi_step",
}


@dataclass(slots=True)
class ExecutionPlan:
    """
    Contrato central de ejecución.

    Representa:

    - Intención transformada en objetivo ejecutable.
    - Contexto requerido.
    - Unidad de ejecución.
    - Steps.
    - Estado.
    - Resultado.

    No:

    - Ejecuta agentes.
    - Ejecuta skills.
    - Gestiona herramientas.
    """

    id: str = field(
        default_factory=lambda: str(uuid.uuid4()),
    )

    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    status: str = "pending"

    priority: int = 0

    original_task: str = ""

    objective: str | None = None

    intent: str | None = None

    intent_category: str | None = None

    execution_mode: str = "single"

    execution_unit_type: str | None = None

    execution_unit: str | None = None

    steps: list[ExecutionStep] = field(
        default_factory=list,
    )

    context_requirements: list[str] = field(
        default_factory=list,
    )

    loaded_context: dict[str, Any] = field(
        default_factory=dict,
    )

    execution_context: dict[str, Any] = field(
        default_factory=dict,
    )

    params: dict[str, Any] = field(
        default_factory=dict,
    )

    constraints: list[str] = field(
        default_factory=list,
    )

    metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    planning_metadata: dict[str, Any] = field(
        default_factory=dict,
    )

    metrics: dict[str, Any] = field(
        default_factory=dict,
    )

    result: Any = None

    error: str | None = None

    max_retries: int = 2

    stop_on_error: bool = True

    # ==================================================
    # Initialization
    # ==================================================

    def __post_init__(
        self,
    ) -> None:

        self.execution_unit_type = self.normalize_unit_type(
            self.execution_unit_type,
        )

        self.execution_mode = self.normalize_execution_mode(
            self.execution_mode,
        )

    # ==================================================
    # Normalization
    # ==================================================

    @classmethod
    def normalize_provider(
        cls,
        provider: str,
    ) -> str:

        if not provider:

            return ""

        value = (
            provider.lower()
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

        return PROVIDER_ALIASES.get(
            value,
            value,
        )

    @classmethod
    def normalize_unit_type(
        cls,
        unit_type: str | None,
    ) -> str | None:

        if not unit_type:

            return None

        value = (
            unit_type.lower()
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

        return UNIT_ALIASES.get(
            value,
            value,
        )

    @classmethod
    def normalize_execution_mode(
        cls,
        mode: str | None,
    ) -> str:

        if not mode:

            return "single"

        return (
            mode.lower()
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
    # Lifecycle
    # ==================================================

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in VALID_STATUS:

            raise ValueError(f"Estado inválido: {status}")

        allowed = VALID_TRANSITIONS.get(
            self.status,
            set(),
        )

        if self.status != status and status not in allowed:

            raise ValueError(f"Transición inválida " f"{self.status} -> {status}")

        self.status = status

    def mark_planned(
        self,
    ) -> None:

        self.set_status(
            "planned",
        )

    def mark_validated(
        self,
    ) -> None:

        self.set_status(
            "validated",
        )

    def mark_running(
        self,
    ) -> None:

        self.set_status(
            "running",
        )

    def mark_partial(
        self,
        result: Any = None,
        error: str | None = None,
    ) -> None:

        self.set_status(
            "partial",
        )

        self.result = result
        self.error = error

    def mark_completed(
        self,
        result: Any = None,
    ) -> None:

        self.set_status(
            "completed",
        )

        self.result = result
        self.error = None

    def mark_failed(
        self,
        error: str,
    ) -> None:

        self.set_status(
            "failed",
        )

        self.error = error

    # ==================================================
    # Validation
    # ==================================================

    def validate(
        self,
    ) -> list[str]:

        errors: list[str] = []

        if not self.original_task.strip():

            errors.append("plan sin tarea original")

        if self.execution_mode not in AVAILABLE_EXECUTION_MODES:

            errors.append("modo de ejecución inválido")

        if self.execution_mode == "single":

            if self.steps:

                errors.append("modo single no permite steps")

            if not self.execution_unit_type:

                errors.append("plan single requiere execution_unit_type")

            if not self.execution_unit:

                errors.append("plan single requiere execution_unit")

        if self.execution_mode == "multi_step":

            if not self.steps:

                errors.append("plan multi_step requiere steps")

            if self.execution_unit:

                errors.append("plan multi_step no debe usar execution_unit")

        if self.execution_unit_type:

            if self.execution_unit_type not in UNIT_TYPES:

                errors.append("tipo de ejecución inválido")

        if self.max_retries < 0:

            errors.append("max_retries no puede ser negativo")

        normalized_providers = []

        for provider in self.context_requirements:

            normalized = self.normalize_provider(
                provider,
            )

            if normalized not in AVAILABLE_CONTEXT_PROVIDERS:

                errors.append(f"provider inválido: {provider}")

            normalized_providers.append(
                normalized,
            )

        if len(normalized_providers) != len(set(normalized_providers)):

            errors.append("providers duplicados")

        if self.status == "completed" and self.error:

            errors.append("plan completado no puede tener error")

        if self.status == "failed" and not self.error:

            errors.append("plan fallido requiere error")

        for step in self.steps:

            errors.extend(step.validate())

        return errors

    # ==================================================
    # Utilities
    # ==================================================

    def clone(
        self,
    ) -> "ExecutionPlan":

        return copy.deepcopy(
            self,
        )

    # ==================================================
    # Steps
    # ==================================================

    def add_step(
        self,
        description: str,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
    ) -> ExecutionStep:

        step = ExecutionStep(
            description=description,
            unit_type=self.normalize_unit_type(
                unit_type,
            ),
            unit_name=unit_name,
            params=params or {},
        )

        self.steps.append(
            step,
        )

        return step

    # ==================================================
    # Metadata helpers
    # ==================================================

    def add_metadata(
        self,
        key: str,
        value: Any,
    ) -> None:

        self.metadata[key] = value

    def requires_context(
        self,
        provider: str,
    ) -> bool:

        normalized = self.normalize_provider(
            provider,
        )

        return normalized in {self.normalize_provider(item) for item in self.context_requirements}

    # ==================================================
    # Serialization
    # ==================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "id": self.id,
            "status": self.status,
            "task": self.original_task,
            "objective": self.objective,
            "intent": self.intent,
            "execution_mode": self.execution_mode,
            "execution_unit": self.execution_unit,
            "steps": [step.to_dict() for step in self.steps],
            "context_requirements": list(self.context_requirements),
            "metadata": dict(self.metadata),
            "result": self.result,
            "error": self.error,
        }
