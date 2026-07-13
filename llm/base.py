from abc import ABC, abstractmethod


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        """
        Genera una respuesta utilizando el proveedor LLM.
        """
        raise NotImplementedError