from abc import ABC, abstractmethod
from typing import Any, ClassVar

from core.execution_plan import ExecutionPlan


class BaseContextProvider(ABC):
    """
    Contrato base para cualquier proveedor de contexto.
    """

    key: ClassVar[str]

    def __init_subclass__(cls, **kwargs):
        """
        Fuerza que cada provider concreto defina su identificador.
        """

        super().__init_subclass__(**kwargs)

        if not getattr(cls, "key", None):
            raise TypeError(f"{cls.__name__} debe definir " "un atributo de clase 'key'.")

    @abstractmethod
    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        """ """
        raise NotImplementedError
