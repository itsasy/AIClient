from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.execution_plan import ExecutionPlan


class BaseWorkflow(ABC):
    """
    Base para todos los workflows de comandos slash.
    """

    name: str = "base"
    description: str = ""

    @abstractmethod
    def execute(self, arguments: str, context: dict[str, Any] | None = None) -> ExecutionPlan:
        """
        Convierte los argumentos del comando en un ExecutionPlan listo para ejecutar.
        """
        raise NotImplementedError

    @abstractmethod
    def validate(self, arguments: str) -> tuple[bool, str]:
        """
        Valida los argumentos antes de ejecutar el workflow.
        """
        raise NotImplementedError
