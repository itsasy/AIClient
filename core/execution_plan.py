from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ExecutionStep:
    """
    Unidad ejecutable dentro de un ExecutionPlan.
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

    result: Any = None

    error: str | None = None

    metadata: dict[str, Any] = field(default_factory=dict)

    def set_status(
        self,
        status: str,
    ) -> None:

        if status not in ExecutionPlan.VALID_STATUS:
            raise ValueError(f"Estado inválido: {status}")

        self.status = status

    def mark_running(self):
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
    """
    Contrato central de ejecución.

    Flujo:

    Intent
      |
      v
    Planner
      |
      v
    ExecutionPlan
      |
      v
    Runtime
      |
      v
    Result
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
        "knowledge",
    }

    AVAILABLE_EXECUTION_MODES = {
        "single",
        "multi_step",
    }

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

    preferred_provider: str | None = None

    temperature: float | None = None

    max_tokens: int | None = None

    system_role: str | None = None

    max_retries: int = 2

    requires_confirmation: bool = False

    requires_self_critic: bool = False

    allow_parallel_steps: bool = False

    stop_on_error: bool = True

    # ======================================================
    # Skills
    # ======================================================

    def add_skill(
        self,
        skill: str,
    ):

        if skill and skill not in self.skills:
            self.skills.append(skill)

    def has_skill(
        self,
        skill: str,
    ) -> bool:

        return skill in self.skills

    @property
    def skill(
        self,
    ):

        return self.skills[0] if self.skills else None

    # ======================================================
    # Context
    # ======================================================

    def add_context_requirement(
        self,
        provider: str,
    ):

        if (
            provider in self.AVAILABLE_CONTEXT_PROVIDERS
            and provider not in self.context_requirements
        ):
            self.context_requirements.append(provider)

    def load_context(
        self,
        name: str,
        value: Any,
    ):

        self.loaded_context[name] = value

    # ======================================================
    # Tools
    # ======================================================

    def add_tool(
        self,
        tool: str,
    ):

        if tool and tool not in self.required_tools:
            self.required_tools.append(tool)

    # ======================================================
    # Steps
    # ======================================================

    def add_step(
        self,
        description: str,
        skill: str | None = None,
        tool: str | None = None,
        params: dict[str, Any] | None = None,
    ):

        self.steps.append(
            ExecutionStep(
                description=description,
                skill=skill,
                tool=tool,
                params=params or {},
            )
        )

    def current_step(self):

        for step in self.steps:

            if step.status != "completed":
                return step

        return None

    # ======================================================
    # Lifecycle
    # ======================================================

    def mark_planned(self):
        self.status = "planned"

    def mark_validated(self):
        self.status = "validated"

    def mark_running(self):
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

    def validate(self):

        errors = []

        if not self.original_task:
            errors.append("original_task vacío")

        if not self.intent:
            errors.append("intent no definido")

        if not self.agent:
            errors.append("agent no definido")

        if self.execution_mode not in self.AVAILABLE_EXECUTION_MODES:
            errors.append("execution_mode inválido")

        invalid_context = [
            x for x in self.context_requirements if x not in self.AVAILABLE_CONTEXT_PROVIDERS
        ]

        for item in invalid_context:
            errors.append(f"context inválido: {item}")

        if self.execution_mode == "multi_step" and not self.steps:
            errors.append("multi_step sin pasos")

        return errors

    # ======================================================
    # Serialization
    # ======================================================

    def to_dict(self):

        return {
            "id": self.id,
            "status": self.status,
            "task": self.original_task,
            "objective": self.objective,
            "intent": self.intent,
            "agent": self.agent,
            "skills": self.skills,
            "context_requirements": self.context_requirements,
            "loaded_context": self.loaded_context,
            "steps": [
                {
                    "description": step.description,
                    "skill": step.skill,
                    "tool": step.tool,
                    "status": step.status,
                    "result": step.result,
                }
                for step in self.steps
            ],
            "result": self.result,
            "error": self.error,
        }

    def __repr__(self):

        return "<ExecutionPlan " f"{self.intent} " f"{self.agent} " f"{self.status}>"
