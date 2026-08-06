from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.execution_plan import ExecutionPlan


class Agent(ABC):
    """
    Contrato base para todos los agentes del sistema.

    Un Agent recibe un ExecutionPlan ya construido.

    Responsabilidades:

    - Ejecutar la intención representada en el plan.
    - Consumir contexto generado por ContextManager.
    - Coordinar herramientas, skills o LLM.

    No:

    - Analiza intención.
    - Construye ExecutionPlans.
    - Resuelve contexto.
    - Selecciona modelos directamente.
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
    # Validation
    # ======================================================

    def validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> list[str]:
        """
        Hook de validación específico.

        Puede comprobar:

        - parámetros requeridos.
        - contexto necesario.
        - capacidades disponibles.
        - compatibilidad del plan.

        No bloquea por defecto.
        """

        return []

    # ======================================================
    # Capability helpers
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
        context: dict[str, Any] | None = None,
    ) -> Any:
        """
        Ejecuta un ExecutionPlan.
        """

        raise NotImplementedError("Los agentes deben implementar process()")
