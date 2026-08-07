from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep


class Skill(ABC):
    """
    Contrato base para Skills ejecutables.

    Una Skill representa una capacidad concreta
    ejecutada dentro de un ExecutionPlan.

    Responsabilidades:

    - Ejecutar una operación específica.
    - Consumir parámetros del step.
    - Utilizar contexto recibido.

    No:

    - Decide ejecución.
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

    aliases: tuple[str, ...] = ()

    capabilities: tuple[str, ...] = ()

    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def normalize(
        value: str,
    ) -> str:

        if not value:
            return ""

        return value.lower().strip().replace("-", "_").replace(" ", "_")

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
            "aliases": list(self.aliases),
            "capabilities": list(self.capabilities),
        }

    # ======================================================
    # Capability helpers
    # ======================================================

    def supports(
        self,
        capability: str,
    ) -> bool:

        normalized = self.normalize(
            capability,
        )

        if not normalized:
            return False

        return normalized in {self.normalize(item) for item in self.capabilities}

    # ======================================================
    # Validation
    # ======================================================

    def validate_step(
        self,
        step: ExecutionStep,
    ) -> list[str]:

        warnings: list[str] = []

        step_name = self.normalize(
            step.unit_name,
        )

        skill_name = self.normalize(
            self.name,
        )

        aliases = {self.normalize(alias) for alias in self.aliases}

        if step_name and step_name != skill_name and step_name not in aliases:

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
    ) -> Any:
        """
        Ejecuta la capacidad.

        Returns:

            Resultado serializable.
        """

        raise NotImplementedError("Las skills deben implementar execute()")
