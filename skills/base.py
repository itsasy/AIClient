from abc import ABC, abstractmethod


class Skill(ABC):

    name: str
    description: str

    @abstractmethod
    def execute(self, **kwargs):
        """
        Siempre devuelve un diccionario.

        {
            "type": "...",
            "payload": ...
        }
        """
        pass