from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)


class Skill(ABC):
    """
    Contrato base para Skills ejecutables.
    """

    name: str = "base"

    description: str = ""

    version: str = "1.0"

    capabilities: tuple[str, ...] = ()

    # ======================================================
    # Metadata
    # ======================================================

    def get_metadata(self) -> dict[str, Any]:

        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": list(self.capabilities),
        }

    # ======================================================
    # Validation
    # ======================================================

    def validate_step(
        self,
        step: ExecutionStep,
    ) -> list[str]:

        warnings = []

        if step.unit_name != self.name:

            warnings.append(
                f"Step apunta a '{step.unit_name}', " f"pero la skill activa es '{self.name}'."
            )

        return warnings

    # ======================================================
    # Execution
    # ======================================================

    @abstractmethod
    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        raise NotImplementedError
