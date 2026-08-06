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

    - Recibir un ExecutionStep.
    - Resolver la Skill mediante SkillManager.
    - Ejecutar Skill.execute().
    - Gestionar retries.
    - Normalizar resultados.

    No:

    - Planifica.
    - Decide Skills.
    - Construye contexto.
    - Modifica ExecutionPlan.
    """

    name = "skill_runtime"

    def __init__(
        self,
        skill_manager: SkillManager | None = None,
    ):

        self.skill_manager = skill_manager or SkillManager()

    # ======================================================
    # Execution
    # ======================================================

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        context = context or {}

        if step.unit_type != "skill":

            return ExecutionResult.fail(
                error=("SkillRuntime recibió " f"unidad inválida: {step.unit_type}"),
                executor=self.name,
                plan_id=plan.id,
            )

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

        start = time.time()

        while retries <= max_retries:

            try:

                logger.info(
                    "Ejecutando skill=%s intento=%s",
                    skill.name,
                    retries + 1,
                )

                step.mark_running()

                result = skill.execute(
                    plan=plan,
                    step=step,
                    context=context,
                )

                normalized = self._normalize_result(
                    result,
                )

                if not normalized["ok"]:

                    raise RuntimeError(
                        normalized.get(
                            "error",
                            "Skill falló",
                        )
                    )

                step.mark_completed(
                    result,
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

                    step.mark_failed(
                        str(exc),
                    )

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

    # ======================================================
    # Helpers
    # ======================================================

    def _normalize_result(
        self,
        result: Any,
    ) -> dict[str, Any]:

        if isinstance(
            result,
            dict,
        ):

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
