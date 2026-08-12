from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from core.execution_plan import ExecutionPlan


class BaseContextProvider(ABC):
    """
    Contrato base para proveedores de contexto.

    Responsabilidades:
    - Identificar el provider mediante `key`.
    - Exponer metadata descriptiva.
    - Cargar y devolver su propio contexto.

    El provider NO debe:
    - mutar el contexto acumulado;
    - asignar context[key];
    - ejecutar otros providers;
    - controlar el lifecycle del contexto.

    ContextManager es responsable de integrar el resultado
    dentro del contexto acumulado.
    """

    key: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        if not getattr(cls, "key", None):
            raise TypeError(f"{cls.__name__} debe definir key")

    def metadata(self) -> dict[str, Any]:
        """
        Devuelve metadata descriptiva del provider.
        """

        return {
            "key": self.key,
            "name": self.name or self.key,
            "description": self.description,
        }

    @abstractmethod
    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Carga el contexto propio del provider.

        Contrato:

        - Sin información disponible → {}
        - Con información disponible → dict
        - Nunca mutar `context`
        - Nunca asignar `context[self.key]`

        ContextManager se encarga de integrar el resultado
        dentro del contexto acumulado.
        """

        raise NotImplementedError
