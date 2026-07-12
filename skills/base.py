from abc import ABC, abstractmethod
from typing import Any


class Skill(ABC):
    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs) -> dict[str, Any]:
        pass