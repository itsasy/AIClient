from __future__ import annotations

from abc import ABC, abstractmethod

from typing import Any, ClassVar

from core.execution_plan import ExecutionPlan


class BaseContextProvider(ABC):
    """
    Contrato base para proveedores de contexto.

    Cada provider debe:

    - Tener una key única.
    - Cargar información dentro del contexto.
    - Ser resoluble mediante ContextRegistry.

    No:

    - Decide cuándo se ejecuta.
    - Modifica ExecutionPlan.
    - Ejecuta agentes o skills.
    """

    key: ClassVar[str] = ""

    name: ClassVar[str] = ""

    description: ClassVar[str] = ""

    def __init_subclass__(
        cls,
        **kwargs,
    ) -> None:

        super().__init_subclass__(**kwargs)

        if not getattr(
            cls,
            "key",
            None,
        ):

            raise TypeError(f"{cls.__name__} debe definir key")

    def metadata(
        self,
    ) -> dict[str, Any]:

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
        Carga información contextual.

        Args:
            plan:
                ExecutionPlan actual.

            context:
                Contexto acumulado hasta este provider.

        Returns:
            Datos aportados por el provider.
        """

        raise NotImplementedError
