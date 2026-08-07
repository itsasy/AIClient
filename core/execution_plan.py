from __future__ import annotations

import copy
import uuid

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

VALID_STATUS = {
    "pending",
    "planned",
    "validated",
    "running",
    "completed",
    "failed",
    "learning",
    "cancelled",
}


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad ejecutable dentro de un ExecutionPlan.

    Representa una acción concreta:
    - Agent.
    - Skill.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    description: str = ""

    unit_type: str | None = None

    unit_name: str | None = None

    params: dict[str, Any] = field(default_factory=dict)

    expected_output: str | None = None

    retries: int = 2

    timeout: int = 120

    depends_on: list[str] = field(default_factory=list)

    status: str = "pending"

    result: Any = None

    error: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    # ======================================================
    # Validation
    # ======================================================

    def validate(
        self,
    ) -> list[str]:

        errors = []

        if not self.description:

            errors.append("step sin descripción")

        if self.unit_type not in {
            "agent",
            "skill",
        }:

            errors.append("tipo de unidad inválido")

        if not self.unit_name:

            errors.append("unidad sin nombre")

        if self.retries < 0:

            errors.append("retries inválido")

        if self.timeout <= 0:

            errors.append("timeout inválido")

        return errors

    # ======================================================
    # Lifecycle
    # ======================================================

    def set_status(
        self,
        status: str,
    ):

        if status not in VALID_STATUS:

            raise ValueError(f"Estado inválido: {status}")

        self.status = status

    def mark_running(
        self,
    ):

        self.set_status("running")

    def mark_completed(
        self,
        result: Any = None,
    ):

        self.status = "completed"

        self.result = result

    def mark_failed(
        self,
        error: str,
    ):

        self.status = "failed"

        self.error = error


@dataclass(slots=True)
class ExecutionPlan:

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
        "project-provider": "project",
        "projects": "project",
        "engram_context": "engram",
        "memory_context": "memory",
        "obsidian_context": "obsidian",
        "document": "documents",
        "docs": "documents",
        "document_context": "documents",
        "standard": "standards",
        "standards_context": "standards",
        "specification": "spec",
        "specifications": "spec",
        "gentleman_context": "gentleman",
    }

    UNIT_TYPES = {
        "agent",
        "skill",
    }

    AVAILABLE_EXECUTION_MODES = {
        "single",
        "multi_step",
    }

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    status: str = "pending"

    priority: int = 0

    original_task: str = ""

    objective: str | None = None

    intent: str | None = None

    intent_category: str | None = None

    execution_mode: str = "single"

    execution_unit_type: str | None = None

    execution_unit: str | None = None

    steps: list[ExecutionStep] = field(default_factory=list)

    context_requirements: list[str] = field(default_factory=list)

    loaded_context: dict[str, Any] = field(default_factory=dict)

    memory_queries: list[str] = field(default_factory=list)

    document_queries: list[str] = field(default_factory=list)

    execution_context: dict[str, Any] = field(default_factory=dict)

    params: dict[str, Any] = field(default_factory=dict)

    constraints: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    planning_metadata: dict[str, Any] = field(default_factory=dict)

    metrics: dict[str, Any] = field(default_factory=dict)

    result: Any = None

    error: str | None = None

    max_retries: int = 2

    stop_on_error: bool = True

    # ======================================================
    # Normalization
    # ======================================================

    @classmethod
    def normalize_provider(
        cls,
        provider: str,
    ) -> str:

        if not provider:

            return provider

        key = (
            provider.lower()
            .strip()
            .replace(
                " ",
                "_",
            )
        )

        return cls.PROVIDER_ALIASES.get(
            key,
            key,
        )

    @classmethod
    def normalize_unit_type(
        cls,
        unit_type: str | None,
    ):

        if not unit_type:

            return None

        return unit_type.lower().strip()

    # ======================================================
    # Context
    # ======================================================

    def add_context_requirement(
        self,
        provider: str,
    ):

        provider = self.normalize_provider(
            provider,
        )

        if (
            provider in self.AVAILABLE_CONTEXT_PROVIDERS
            and provider not in self.context_requirements
        ):

            self.context_requirements.append(
                provider,
            )

    def validate_context_requirements(
        self,
    ):

        invalid = []

        normalized = []

        for provider in self.context_requirements:

            canonical = self.normalize_provider(
                provider,
            )

            if canonical not in self.AVAILABLE_CONTEXT_PROVIDERS:

                invalid.append(
                    provider,
                )

            else:

                normalized.append(
                    canonical,
                )

        self.context_requirements = list(
            dict.fromkeys(
                normalized,
            )
        )

        return invalid

    # ======================================================
    # Steps
    # ======================================================

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

    def current_step(
        self,
    ) -> ExecutionStep | None:

        for step in self.steps:

            if step.status != "completed":

                return step

        return None

    # ======================================================
    # Lifecycle
    # ======================================================

    def mark_planned(
        self,
    ):

        self.status = "planned"

    def mark_running(
        self,
    ):

        self.status = "running"

    def mark_completed(
        self,
        result=None,
    ):

        self.status = "completed"

        self.result = result

    def mark_failed(
        self,
        error: str,
    ):

        self.status = "failed"

        self.error = error

    # ======================================================
    # Validation
    # ======================================================

    def validate(
        self,
    ):

        errors = []

        if not self.original_task:

            errors.append("original_task vacío")

        if not self.intent:

            errors.append("intent no definido")

        if self.execution_mode not in self.AVAILABLE_EXECUTION_MODES:

            errors.append("execution_mode inválido")

        if self.execution_unit_type:

            if self.execution_unit_type not in self.UNIT_TYPES:

                errors.append("execution_unit_type inválido")

            if not self.execution_unit:

                errors.append("execution_unit no definido")

        if not self.execution_unit_type and not self.steps:

            errors.append("sin unidad de ejecución")

        errors.extend(
            [f"context inválido: {item}" for item in self.validate_context_requirements()]
        )

        if self.execution_mode == "multi_step" and not self.steps:

            errors.append("multi_step sin pasos")

        if self.execution_mode == "single" and self.steps:

            errors.append("single no puede contener steps")

        # ----------------------------------------------
        # Step validation
        # ----------------------------------------------

        step_ids = {step.id for step in self.steps}

        for index, step in enumerate(self.steps):

            for error in step.validate():

                errors.append(f"step[{index}] {error}")

            for dependency in step.depends_on:

                if dependency not in step_ids:

                    errors.append(f"step[{index}] dependencia inexistente: {dependency}")

        return errors

    # ======================================================
    # Utilities
    # ======================================================

    def clone(
        self,
    ) -> "ExecutionPlan":

        return copy.deepcopy(
            self,
        )

    # ======================================================
    # Serialization
    # ======================================================

    def to_dict(
        self,
    ):

        return {
            "id": self.id,
            "status": self.status,
            "task": self.original_task,
            "objective": self.objective,
            "intent": self.intent,
            "execution_unit_type": self.execution_unit_type,
            "execution_unit": self.execution_unit,
            "steps": [
                {
                    "id": step.id,
                    "description": step.description,
                    "unit_type": step.unit_type,
                    "unit_name": step.unit_name,
                    "status": step.status,
                    "depends_on": step.depends_on,
                    "result": step.result,
                    "error": step.error,
                }
                for step in self.steps
            ],
            "result": self.result,
            "error": self.error,
        }

    def __repr__(
        self,
    ):

        return (
            "<ExecutionPlan "
            f"{self.intent} "
            f"{self.execution_unit_type}:"
            f"{self.execution_unit} "
            f"{self.status}>"
        )
