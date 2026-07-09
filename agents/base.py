from abc import ABC, abstractmethod


class Agent(ABC):

    name: str
    role: str

    @abstractmethod
    def process(self, task: str):
        pass