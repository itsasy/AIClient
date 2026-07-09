from abc import ABC, abstractmethod
from typing import Dict

class Skill(ABC):
    name: str
    description: str
    
    @abstractmethod
    def execute(self, **kwargs) -> str:
        pass
    
    def get_prompt(self, task: str) -> str:
        return f"[Skill: {self.name}] {task}"
