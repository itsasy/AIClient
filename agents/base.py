from abc import ABC, abstractmethod

from core.execution_plan import ExecutionPlan


class Agent(ABC):

    name = "base"

    @abstractmethod
    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:
        raise NotImplementedError("Los agentes deben implementar process()")
