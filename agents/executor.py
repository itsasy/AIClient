from __future__ import annotations

import logging

from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):

    name = "executor"

    description = "Agente encargado de ejecutar operaciones internas."

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> Any:

        context = context or {}

        logger.info(
            "ExecutorAgent ejecutando step=%s",
            step.id,
        )

        return {
            "ok": True,
            "result": {
                "step_id": step.id,
                "description": step.description,
                "status": "completed",
            },
            "error": None,
        }
