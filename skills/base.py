from __future__ import annotations

from abc import ABC, abstractmethod

from core.execution_plan import ExecutionPlan, ExecutionStep


class Skill(ABC):
    """
    Contrato base para Skills.

    Una Skill representa una capacidad ejecutable.

    No:

    - Decide agentes.
    - Gestiona contexto.
    - Planifica.
    """

    name: str = "base"

    @abstractmethod
    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict,
    ):
        raise NotImplementedError
