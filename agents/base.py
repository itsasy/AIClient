from abc import ABC, abstractmethod

from core.execution_plan import ExecutionPlan


class Agent(ABC):
    """
    Clase base para todos los agentes.

    Los agentes reciben un ExecutionPlan ya resuelto.
    No deben analizar intención ni crear planes nuevos.
    """

    name = "base"

    @abstractmethod
    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:
        """
        Ejecuta un plan previamente construido.

        Args:
            plan:
                Plan de ejecución generado por Orchestrator.

            context:
                Contexto agregado por ContextManager.

        Returns:
            Resultado de ejecución.
        """
        raise NotImplementedError("Los agentes deben implementar process()")
