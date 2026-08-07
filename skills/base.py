from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep


class Skill(ABC):
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    aliases: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()

    @abstractmethod
    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> Any:
        raise NotImplementedError("Las skills deben implementar execute()")
