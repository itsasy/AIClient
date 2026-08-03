from __future__ import annotations

import uuid

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class ExecutionStep:
    """
    Paso individual de un ExecutionPlan.
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


@dataclass(slots=True)
class ExecutionPlan:
    """
    Contrato único de ejecución.

    Todo el sistema trabaja únicamente con ExecutionPlan.

    El contexto requerido se define mediante:
        context_requirements

    Ningún componente debe depender de estructuras
    anteriores al ExecutionPlan.
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

    # ---------------------------------------------------------
    # Identidad
    # ---------------------------------------------------------

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = field(default_factory=datetime.utcnow)

    status: str = "pending"

    priority: int = 0

    # ---------------------------------------------------------
    # Solicitud original
    # ---------------------------------------------------------

    original_task: str = ""

    objective: str | None = None

    intent: str | None = None

    intent_category: str | None = None

    # ---------------------------------------------------------
    # Ejecución
    # ---------------------------------------------------------

    execution_mode: str = "single"

    agent: str | None = None

    skills: list[str] = field(default_factory=list)

    required_tools: list[str] = field(default_factory=list)

    steps: list[ExecutionStep] = field(default_factory=list)

    # ---------------------------------------------------------
    # Contexto
    # ---------------------------------------------------------

    context_requirements: list[str] = field(default_factory=list)

    memory_queries: list[str] = field(default_factory=list)

    document_queries: list[str] = field(default_factory=list)

    # ---------------------------------------------------------
    # Parámetros
    # ---------------------------------------------------------

    params: dict[str, Any] = field(default_factory=dict)

    constraints: list[str] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    metrics: dict[str, Any] = field(default_factory=dict)

    # ---------------------------------------------------------
    # Configuración LLM
    # ---------------------------------------------------------

    preferred_provider: str | None = None

    temperature: float | None = None

    max_tokens: int | None = None

    system_role: str | None = None

    # ---------------------------------------------------------
    # Configuración ejecución
    # ---------------------------------------------------------

    max_retries: int = 2

    requires_confirmation: bool = False

    requires_self_critic: bool = False

    allow_parallel_steps: bool = False

    stop_on_error: bool = True

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------

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

    def requires_context(
        self,
        provider: str,
    ) -> bool:

        return provider in self.context_requirements

    def requires_tool(
        self,
        tool: str,
    ) -> bool:

        return tool in self.required_tools

    def uses_skill(
        self,
        skill: str,
    ) -> bool:

        return skill in self.skills

    def validate_context_requirements(self) -> list[str]:

        return [
            provider
            for provider in self.context_requirements
            if provider not in self.AVAILABLE_CONTEXT_PROVIDERS
        ]

    def to_dict(self) -> dict[str, Any]:

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
            "memory_queries": self.memory_queries,
            "document_queries": self.document_queries,
            "params": self.params,
            "constraints": self.constraints,
            "metadata": self.metadata,
            "metrics": self.metrics,
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

    def __repr__(self) -> str:

        return (
            f"<ExecutionPlan("
            f"intent={self.intent}, "
            f"agent={self.agent}, "
            f"skills={self.skills}, "
            f"steps={len(self.steps)}, "
            f"status={self.status})>"
        )
