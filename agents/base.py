from abc import ABC, abstractmethod


class Agent(ABC):
    name: str = "base"

    @abstractmethod
    def process(
        self,
        task: str,
        context: dict | None = None,
        skill_name: str | None = None,
        skill_params: dict | None = None,
    ) -> str:
        raise NotImplementedError