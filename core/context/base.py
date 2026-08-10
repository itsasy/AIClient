from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from core.execution_plan import ExecutionPlan


class BaseContextProvider(ABC):
    """
    Contrato base para proveedores de contexto.

    Un provider:
        - Tiene una key única.
        - Carga información contextual.
        - Devuelve exclusivamente sus propios datos.

    Un provider NO:
        - Modifica ExecutionPlan.
        - Ejecuta Agents.
        - Ejecuta Skills.
        - Construye prompts.
        - Modifica directamente el contexto acumulado.
    """

    key: ClassVar[str] = ""
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        if not getattr(cls, "key", None):
            raise TypeError(f"{cls.__name__} debe definir key")

    def metadata(self) -> dict[str, Any]:
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
        Devuelve los datos contextuales producidos por el provider.
        """

        raise NotImplementedError
