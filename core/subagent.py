from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class Subagent:
    """
    Ejecuta unidades pequeñas de un ExecutionPlan.

    Responsabilidades:

    - Resolver ExecutionStep.
    - Ejecutar Skills.
    - Manejar retries.
    - Devolver resultado normalizado.

    No:

    - Analiza intención.
    - Crea planes.
    - Ejecuta self critic.
    - Gestiona memoria.
    """

    def __init__(self):

        self.skills = SkillManager()

    # ==========================================================
    # Execute
    # ==========================================================

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:

        context = context or {}

        retries = 0

        max_retries = step.retries or plan.max_retries

        while retries <= max_retries:

            try:

                logger.info(
                    "Ejecutando step: %s",
                    step.description,
                )

                step.status = "running"

                result = self.skills.execute(
                    step.skill,
                    **step.params,
                )

                step.status = "completed"

                return {
                    "success": True,
                    "result": result,
                }

            except Exception as exc:

                retries += 1

                logger.exception(
                    "Error ejecutando step %s",
                    step.description,
                )

                if retries > max_retries:

                    step.status = "failed"

                    return {
                        "success": False,
                        "error": str(exc),
                    }

        step.status = "failed"

        return {
            "success": False,
            "error": "Max retries alcanzado.",
        }

    # ==========================================================
    # Helpers
    # ==========================================================

    @staticmethod
    def _extract_output(
        result: Any,
    ) -> str:

        if not isinstance(result, dict):

            return str(result)

        payload = result.get(
            "payload",
            {},
        )

        return payload.get("output") or payload.get("message") or str(result)
