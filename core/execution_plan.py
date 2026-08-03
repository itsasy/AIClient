from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ExecutionStep:
    """
    Paso individual de ejecución.

    Representa una acción dentro de un flujo.
    """

    description: str

    skill: str | None = None

    tool: str | None = None

    provider: str | None = None

    params: dict[str, Any] = field(default_factory=dict)

    expected_output: str | None = None

    retries: int = 2

    timeout: int = 120

    status: str = "pending"

    metadata: dict[str, Any] = field(default_factory=dict)

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in ExecutionPlan.VALID_STATUS:
            raise ValueError(f"Estado inválido: {status}")

        self.status = status

    def mark_running(
        self,
    ) -> None:

        self.set_status(
            "running",
        )

    def mark_completed(
        self,
    ) -> None:

        self.set_status(
            "completed",
        )

    def mark_failed(
        self,
    ) -> None:

        self.set_status(
            "failed",
        )


@dataclass(slots=True)
class ExecutionPlan:
    """
    Contrato central del sistema.
    """

    AVAILABLE_CONTEXT_PROVIDERS = {
        "project",
        "engram",
        "memory",
        "obsidian",
        "documents",
        "spec",
        "standards",
        "gentleman",
    }

    AVAILABLE_EXECUTION_MODES = {
        "single",
        "multi_step",
    }

    VALID_STATUS = {
        "pending",
        "running",
        "completed",
        "failed",
        "cancelled",
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

    agent: str | None = None

    skills: list[str] = field(default_factory=list)

    required_tools: list[str] = field(default_factory=list)

    steps: list[ExecutionStep] = field(default_factory=list)

    context_requirements: list[str] = field(default_factory=list)

    memory_queries: list[str] = field(default_factory=list)

    document_queries: list[str] = field(default_factory=list)

    execution_context: dict[str, Any] = field(default_factory=dict)

    params: dict[str, Any] = field(default_factory=dict)

    constraints: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    metrics: dict[str, Any] = field(default_factory=dict)

    result: Any = None

    error: str | None = None

    preferred_provider: str | None = None

    temperature: float | None = None

    max_tokens: int | None = None

    system_role: str | None = None

    max_retries: int = 2

    requires_confirmation: bool = False

    requires_self_critic: bool = False

    allow_parallel_steps: bool = False

    stop_on_error: bool = True

    # ==========================================================
    # Skills
    # ==========================================================

    def primary_skill(
        self,
    ) -> str | None:

        return self.skills[0] if self.skills else None

    @property
    def skill(
        self,
    ) -> str | None:

        return self.primary_skill()

    def has_skill(
        self,
        skill: str,
    ) -> bool:

        return skill in self.skills

    def add_skill(
        self,
        skill: str,
    ) -> None:

        if skill and skill not in self.skills:
            self.skills.append(skill)

    # ==========================================================
    # Contexto
    # ==========================================================

    def requires_context(
        self,
        provider: str,
    ) -> bool:

        return provider in self.context_requirements

    def add_context_requirement(
        self,
        provider: str,
    ) -> None:

        if (
            provider in self.AVAILABLE_CONTEXT_PROVIDERS
            and provider not in self.context_requirements
        ):
            self.context_requirements.append(provider)

    def validate_context_requirements(
        self,
    ) -> list[str]:

        return [
            item
            for item in self.context_requirements
            if item not in self.AVAILABLE_CONTEXT_PROVIDERS
        ]

    # ==========================================================
    # Tools
    # ==========================================================

    def requires_tool(
        self,
        tool: str,
    ) -> bool:

        return tool in self.required_tools

    def add_tool(
        self,
        tool: str,
    ) -> None:

        if tool and tool not in self.required_tools:
            self.required_tools.append(tool)

    # ==========================================================
    # Params
    # ==========================================================

    def add_param(
        self,
        key: str,
        value: Any,
    ) -> None:

        self.params[key] = value

    def add_constraint(
        self,
        value: str,
    ) -> None:

        if value and value not in self.constraints:
            self.constraints.append(value)

    # ==========================================================
    # Steps
    # ==========================================================

    def add_step(
        self,
        description: str,
        skill: str | None = None,
        tool: str | None = None,
        provider: str | None = None,
        params: dict[str, Any] | None = None,
    ) -> None:

        self.steps.append(
            ExecutionStep(
                description=description,
                skill=skill,
                tool=tool,
                provider=provider,
                params=params or {},
            )
        )

    def update_step_status(
        self,
        index: int,
        status: str,
    ) -> None:

        if index < 0 or index >= len(self.steps):
            raise IndexError("Índice de step inválido.")

        self.steps[index].set_status(
            status,
        )

    def is_multistep(
        self,
    ) -> bool:

        return self.execution_mode == "multi_step"

    # ==========================================================
    # Estado
    # ==========================================================

    def mark_completed(
        self,
        result: Any = None,
    ) -> None:

        self.status = "completed"
        self.result = result

    def mark_failed(
        self,
        error: str,
    ) -> None:

        self.status = "failed"
        self.error = error

    # ==========================================================
    # Validación
    # ==========================================================

    def validate(
        self,
    ) -> list[str]:

        errors = []

        if not self.original_task:
            errors.append("original_task vacío")

        if self.intent is None:
            errors.append("intent no definido")

        if self.agent is None:
            errors.append("agent no definido")

        if self.agent == "executor" and not self.skills:
            errors.append("executor sin skills")

        if self.execution_mode not in self.AVAILABLE_EXECUTION_MODES:
            errors.append("execution_mode inválido")

        errors.extend(
            [f"context inválido: {item}" for item in self.validate_context_requirements()]
        )

        if len(self.skills) != len(set(self.skills)):
            errors.append("skills duplicadas")

        if self.execution_mode == "multi_step" and not self.steps:
            errors.append("multi_step sin steps definidos")

        return errors

    # ==========================================================
    # Serialización
    # ==========================================================

    def to_dict(
        self,
    ) -> dict[str, Any]:

        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            "status": self.status,
            "priority": self.priority,
            "original_task": self.original_task,
            "objective": self.objective,
            "intent": self.intent,
            "intent_category": self.intent_category,
            "execution_mode": self.execution_mode,
            "agent": self.agent,
            "skills": self.skills,
            "required_tools": self.required_tools,
            "context_requirements": self.context_requirements,
            "params": self.params,
            "constraints": self.constraints,
            "metadata": self.metadata,
            "metrics": self.metrics,
            "execution_context": self.execution_context,
            "result": self.result,
            "error": self.error,
            "preferred_provider": self.preferred_provider,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "system_role": self.system_role,
            "max_retries": self.max_retries,
            "requires_confirmation": self.requires_confirmation,
            "requires_self_critic": self.requires_self_critic,
            "allow_parallel_steps": self.allow_parallel_steps,
            "stop_on_error": self.stop_on_error,
            "steps": [
                {
                    "description": step.description,
                    "skill": step.skill,
                    "tool": step.tool,
                    "provider": step.provider,
                    "params": step.params,
                    "expected_output": step.expected_output,
                    "retries": step.retries,
                    "timeout": step.timeout,
                    "status": step.status,
                    "metadata": step.metadata,
                }
                for step in self.steps
            ],
        }

    # ==========================================================
    # Debug
    # ==========================================================

    def __repr__(
        self,
    ) -> str:

        return (
            "<ExecutionPlan("
            f"intent={self.intent}, "
            f"agent={self.agent}, "
            f"skills={self.skills}, "
            f"steps={len(self.steps)}, "
            f"status={self.status})>"
        )
