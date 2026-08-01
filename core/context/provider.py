from abc import ABC, abstractmethod


class ContextProvider(ABC):

    @abstractmethod
    def load(
        self,
        plan,
        context: dict,
    ) -> None:
        """
        Agrega información al contexto.
        """
