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

    Una Skill representa una capacidad concreta
    que puede ser ejecutada dentro de un ExecutionPlan.

    Responsabilidades:

    - Ejecutar una operación específica.
    - Consumir parámetros del step.
    - Utilizar contexto proporcionado.

    No:

    - Decide cuándo ejecutarse.
    - Construye planes.
    - Gestiona retries.
    - Selecciona otras skills.
    """

    # ======================================================
    # Identity
    # ======================================================

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
            "capabilities": list(
                self.capabilities,
            ),
        }

    # ======================================================
    # Capability helpers
    # ======================================================

    def supports(
        self,
        capability: str,
    ) -> bool:

        return capability in self.capabilities

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
                (f"Step apunta a '{step.unit_name}', " f"pero la skill activa es '{self.name}'.")
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
        """
        Ejecuta la capacidad.

        Returns:

            Resultado serializable.
        """

        raise NotImplementedError("Las skills deben implementar execute()")
