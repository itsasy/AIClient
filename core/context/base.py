from abc import ABC, abstractmethod

from core.execution_plan import ExecutionPlan


class BaseContextProvider(ABC):
    """
    Contrato base para cualquier proveedor de contexto.
    """

    key: str = ""

    @abstractmethod
    def load(
        self,
        plan: ExecutionPlan,
        context: dict,
    ) -> None:
        raise NotImplementedError
