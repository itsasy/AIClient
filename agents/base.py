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
    - Delegar tareas específicas al LLMRouter o herramientas.

    No debe:

    - Analizar intención.
    - Crear ExecutionPlans.
    - Resolver contexto.
    - Elegir proveedores LLM directamente.
    """

    name: str = "base"

    @abstractmethod
    def process(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:
        """
        Ejecuta un ExecutionPlan.

        Args:
            plan:
                Contrato central de ejecución.

            context:
                Contexto construido por ContextManager.

        Returns:
            Respuesta generada por el agente.
        """

        raise NotImplementedError("Los agentes deben implementar process()")

    # ==========================================================
    # Validation hook
    # ==========================================================

    def validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> list[str]:
        """
        Hook opcional para validaciones específicas.

        Ejemplo:

        - CoderAgent puede requerir lenguaje.
        - ExecutorAgent puede requerir comandos.
        - ArchitectAgent puede requerir contexto de proyecto.

        No bloquea la ejecución por defecto.
        """

        return []
