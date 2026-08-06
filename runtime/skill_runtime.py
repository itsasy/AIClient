from __future__ import annotations

import logging
import time

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from core.execution_result import ExecutionResult

from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class SkillRuntime:
    """
    Runtime encargado de ejecutar Skills.

    Responsabilidades:

    - Resolver Skills.
    - Ejecutar Skill.execute().
    - Gestionar retries.
    - Normalizar resultados.

    No:

    - Gestiona lifecycle del step.
    - Planifica.
    - Construye contexto.
    """

    name = "skill_runtime"

    def __init__(
        self,
        skill_manager: SkillManager | None = None,
    ):

        self.skill_manager = skill_manager or SkillManager()

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        context = context or {}

        skill = self.skill_manager.get(
            step.unit_name,
        )

        if skill is None:

            return ExecutionResult.fail(
                error=(f"Skill no encontrada: " f"{step.unit_name}"),
                executor=self.name,
                plan_id=plan.id,
            )

        retries = 0

        max_retries = step.retries if step.retries is not None else plan.max_retries

        while retries <= max_retries:

            try:

                result = skill.execute(
                    plan=plan,
                    step=step,
                    context=context,
                )

                normalized = self._normalize_result(result)

                if not normalized["ok"]:

                    raise RuntimeError(
                        normalized.get(
                            "error",
                            "Skill falló",
                        )
                    )

                return ExecutionResult.ok(
                    output=result,
                    executor=f"skill:{skill.name}",
                    plan_id=plan.id,
                )

            except Exception as exc:

                retries += 1

                logger.exception(
                    "Error skill=%s intento=%s",
                    skill.name,
                    retries,
                )

                if retries > max_retries:

                    return ExecutionResult.fail(
                        error=str(exc),
                        executor=f"skill:{skill.name}",
                        plan_id=plan.id,
                    )

        return ExecutionResult.fail(
            error="Max retries alcanzado.",
            executor=self.name,
            plan_id=plan.id,
        )

    def _normalize_result(
        self,
        result: Any,
    ) -> dict[str, Any]:

        if isinstance(result, dict):

            if "ok" in result:

                return result

            return {
                "ok": True,
                "result": result,
                "error": None,
            }

        return {
            "ok": True,
            "result": result,
            "error": None,
        }
