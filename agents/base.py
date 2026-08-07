from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep


class Agent(ABC):
    """
    Contrato base para agentes.

    Un Agent ejecuta una intención
    representada en un ExecutionPlan.
    """

    name: str = "base"

    description: str = ""

    version: str = "1.0"

    capabilities: tuple[str, ...] = ()

    # ======================================================
    # Metadata
    # ======================================================

    def get_metadata(
        self,
    ) -> dict[str, Any]:

        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": list(self.capabilities),
        }

    # ======================================================
    # Validation
    # ======================================================

    def validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> list[str]:

        return []

    # ======================================================
    # Capabilities
    # ======================================================

    def supports(
        self,
        capability: str,
    ) -> bool:

        return capability in self.capabilities

    # ======================================================
    # Execution
    # ======================================================

    @abstractmethod
    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> Any:

        raise NotImplementedError("Los agentes deben implementar process()")
