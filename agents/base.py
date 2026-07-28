from abc import ABC, abstractmethod


class Agent(ABC):
    name: str = "base"

    @abstractmethod
    def process(
        self,
        task: str,
        context: dict[str, object] | None = None,
        skill_name: str | None = None,
        skill_params: dict[str, object] | None = None,
    ) -> str:
        raise NotImplementedError("Los agentes deben implementar process()")
