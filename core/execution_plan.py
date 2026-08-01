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
    """
    Representa la intención ya interpretada del usuario.

    Este objeto reemplaza:
    - IntentResult
    - skill_name
    - skill_params
    - parte de la lógica del Orchestrator

    Todo el sistema trabaja sobre este contrato.
    """

    original_task: str

    intent: str | None = None

    objective: str | None = None

    agent: str | None = None

    skill: str | None = None

    params: dict[str, Any] = field(default_factory=dict)

    context_requirements: list[str] = field(default_factory=list)

    constraints: list[str] = field(default_factory=list)

    steps: list[ExecutionStep] = field(default_factory=list)

    execution_mode: str = "single"

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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task": self.original_task,
            "intent": self.intent,
            "objective": self.objective,
            "agent": self.agent,
            "skill": self.skill,
            "params": self.params,
            "context_requirements": self.context_requirements,
            "constraints": self.constraints,
            "execution_mode": self.execution_mode,
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
