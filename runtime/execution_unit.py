from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.execution_plan import ExecutionPlan


class ExecutionUnit(ABC):

    name: str = "unknown"

    @abstractmethod
    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> Any:

        raise NotImplementedError
