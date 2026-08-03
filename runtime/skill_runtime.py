from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class SkillRuntime:
    """
    Runtime encargado de ejecutar Skills.

    Responsabilidades:

    - Resolver Skill.
    - Ejecutar SkillManager.
    - Gestionar lifecycle del step.
    - Aplicar retries.
    - Normalizar resultados.

    No:

    - Selecciona agentes.
    - Construye contexto.
    - Decide planificación.
    """

    def __init__(
        self,
        skill_manager: SkillManager | None = None,
    ):

        self.skills = skill_manager or SkillManager()

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
                    "Ejecutando skill=%s step=%s",
                    step.skill,
                    step.description,
                )

                step.mark_running()

                result = self.skills.execute(
                    step.skill,
                    **step.params,
                )

                step.mark_completed(
                    result,
                )

                return {
                    "success": True,
                    "result": result,
                }

            except Exception as exc:

                retries += 1

                logger.exception(
                    "Error ejecutando skill=%s intento=%s",
                    step.skill,
                    retries,
                )

                if retries > max_retries:

                    step.mark_failed(
                        str(exc),
                    )

                    return {
                        "success": False,
                        "error": str(exc),
                    }

        return {
            "success": False,
            "error": "Max retries alcanzado.",
        }
