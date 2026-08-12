from __future__ import annotations

from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.standards_learner import StandardsLearner


class StandardsProvider(BaseContextProvider):
    """
    Proveedor de estándares aprendidos del proyecto.

    Responsabilidades:
    - Exponer estándares persistidos.
    - No ejecutar aprendizaje.
    - No inicializar LLM.
    - No mutar el contexto acumulado.

    ContextManager se encarga de integrar el resultado.
    """

    key = "standards"
    name = "Standards"
    description = "Estándares aprendidos del proyecto."

    def __init__(self) -> None:
        self.standards = StandardsLearner()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        standards = self.standards.list_standards()

        if not standards:
            return {}

        return {
            "learned_standards": standards,
        }
