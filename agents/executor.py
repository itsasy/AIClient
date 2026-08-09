from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class ExecutorAgent(Agent):
    """
    Ejecuta skills definidas en un ExecutionPlan.

    Recibe un plan y ejecuta la skill correspondiente.
    No decide qué skill ejecutar, solo la ejecuta.
    """

    name = "executor"
    description = "Ejecuta skills definidas en el plan."
    version = "2.0"
    capabilities = ("skill_execution",)

    def __init__(self):
        self.skill_manager = SkillManager()

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Ejecuta la skill especificada en el step.
        """
        skill_name = step.unit_name
        params = step.params or {}

        if not skill_name:
            return {
                "ok": False,
                "result": None,
                "error": "No se especificó una skill para ejecutar.",
            }

        logger.info("Ejecutando skill: %s", skill_name)

        try:
            result = self.skill_manager.execute(skill_name, plan=plan, step=step, context=context)
            return {
                "ok": True,
                "result": result,
                "error": None,
            }
        except Exception as e:
            logger.exception("Error ejecutando skill %s", skill_name)
            return {
                "ok": False,
                "result": None,
                "error": str(e),
            }
