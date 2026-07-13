from abc import ABC, abstractmethod


class Agent(ABC):
    name: str
    role: str
    skills: tuple[str, ...] = ()

    @abstractmethod
    def process(
        self,
        task: str,
        context: dict | None = None,
    ) -> str:
        raise NotImplementedError