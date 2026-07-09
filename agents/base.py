from abc import ABC, abstractmethod

class Agent(ABC):
    name: str
    role: str
    skills: list
    
    @abstractmethod
    def process(self, task: str) -> str:
        pass
