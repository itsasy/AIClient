from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):
    """
    DEPRECATED.

    Históricamente ejecutaba skills. Esa responsabilidad pertenece
    exclusivamente a UnitDispatcher + ExecutionEngine.

    No debe usarse en nuevos planes.
    """

    name = "executor"
    description = "DEPRECATED. No usar. La ejecución de skills la realiza " "UnitDispatcher."
    version = "2.1-deprecated"
    capabilities = ()

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger.warning(
            "ExecutorAgent está deprecado. "
            "El plan debe declarar unit_type='skill' y dejar "
            "que UnitDispatcher ejecute la skill."
        )
        return {
            "ok": False,
            "result": None,
            "error": (
                "ExecutorAgent está deprecado. " "Usa unit_type='skill' en el ExecutionStep."
            ),
            "deprecated": True,
        }
