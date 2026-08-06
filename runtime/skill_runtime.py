from __future__ import annotations

import logging

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
    - Ejecutar Skills.
    - Gestionar retries.
    - Normalizar resultados.

    No:

    - Planifica.
    - Selecciona Skills.
    - Construye contexto.
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
    ) -> ExecutionResult:

        context = context or {}

        if step.unit_type != "skill":

            return ExecutionResult.fail(
                error=("SkillRuntime recibió unidad inválida: " f"{step.unit_type}"),
                executor="skill_runtime",
                plan_id=plan.id,
            )

        retries = 0

        max_retries = step.retries if step.retries is not None else plan.max_retries

        while retries <= max_retries:

            try:

                logger.info(
                    "Ejecutando skill=%s intento=%s",
                    step.unit_name,
                    retries + 1,
                )

                step.mark_running()

                result = self.skills.execute(
                    step.unit_name,
                    plan=plan,
                    step=step,
                    context=context,
                )

                normalized = self._validate_result(
                    result,
                )

                if not normalized["ok"]:

                    raise RuntimeError(
                        normalized.get(
                            "error",
                            "Skill falló sin error especificado",
                        )
                    )

                step.mark_completed(
                    result,
                )

                return ExecutionResult.ok(
                    output=result,
                    executor=f"skill:{step.unit_name}",
                    plan_id=plan.id,
                )

            except Exception as exc:

                retries += 1

                logger.exception(
                    "Error skill=%s intento=%s",
                    step.unit_name,
                    retries,
                )

                if retries > max_retries:

                    step.mark_failed(
                        str(exc),
                    )

                    return ExecutionResult.fail(
                        error=str(exc),
                        executor=f"skill:{step.unit_name}",
                        plan_id=plan.id,
                    )

        return ExecutionResult.fail(
            error="Max retries alcanzado.",
            executor=f"skill:{step.unit_name}",
            plan_id=plan.id,
        )

    def _validate_result(
        self,
        result: Any,
    ) -> dict:

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
