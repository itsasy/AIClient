from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid
from datetime import datetime


@dataclass(slots=True)
class ExecutionStep:
    """
    Paso individual dentro de una ejecución compleja.
    Usado principalmente por PlannerAgent y SDD.
    """

    description: str

    skill: str | None = None

    params: dict[str, Any] = field(default_factory=dict)

    status: str = "pending"


@dataclass(slots=True)
class ExecutionPlan:

    original_task: str

    intent: str | None = None

    intent_category: str | None = None

    objective: str | None = None

    agent: str | None = None

    skill: str | None = None

    params: dict[str, Any] = field(default_factory=dict)

    context_requirements: list[str] = field(default_factory=list)

    constraints: list[str] = field(default_factory=list)

    steps: list[ExecutionStep] = field(default_factory=list)

    execution_mode: str = "single"

    preferred_provider: str | None = None

    requires_confirmation: bool = False

    requires_self_critic: bool = False

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_step(
        self,
        description: str,
        skill: str | None = None,
        params: dict[str, Any] | None = None,
    ):
        self.steps.append(
            ExecutionStep(
                description=description,
                skill=skill,
                params=params or {},
            )
        )

    def requires_context(
        self,
        provider: str,
    ) -> bool:
        return provider in self.context_requirements

    def has_steps(self) -> bool:
        return len(self.steps) > 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat(),
            # Información original
            "original_task": self.original_task,
            # Clasificación de intención
            "intent": self.intent,
            "intent_category": self.intent_category,
            # Ejecución
            "objective": self.objective,
            "agent": self.agent,
            "skill": self.skill,
            # Datos de ejecución
            "params": self.params,
            # Contexto requerido
            "context_requirements": self.context_requirements,
            # Reglas
            "constraints": self.constraints,
            # Control
            "execution_mode": self.execution_mode,
            "preferred_provider": self.preferred_provider,
            "requires_confirmation": self.requires_confirmation,
            "requires_self_critic": self.requires_self_critic,
            # Pasos SDD
            "steps": [
                {
                    "description": step.description,
                    "skill": step.skill,
                    "params": step.params,
                    "status": step.status,
                }
                for step in self.steps
            ],
        }

    def __repr__(self):
        return (
            f"<ExecutionPlan "
            f"intent={self.intent} "
            f"agent={self.agent} "
            f"skill={self.skill}>"
        )
