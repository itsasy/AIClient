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
    - Validar compatibilidad Skill/Step.
    - Ejecutar Skill.execute().
    - Gestionar retries.
    - Normalizar resultados.
    - Actualizar lifecycle del step.

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

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
            "duration": 0,
        }

    # ======================================================
    # Execution
    # ======================================================

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        start = time.time()

        self.metrics["executions"] += 1

        context = context or {}

        if step.unit_type != "skill":

            return ExecutionResult.fail(
                error=("SkillRuntime recibió " f"unit_type inválido: {step.unit_type}"),
                executor=self.name,
                plan_id=plan.id,
            )

        validation_errors = step.validate()

        if validation_errors:

            return ExecutionResult.fail(
                error=str(validation_errors),
                executor=self.name,
                plan_id=plan.id,
            )

        skill = self.skill_manager.get(
            step.unit_name,
        )

        if skill is None:

            return ExecutionResult.fail(
                error=f"Skill no encontrada: {step.unit_name}",
                executor=self.name,
                plan_id=plan.id,
            )

        # ----------------------------------------------
        # Skill validation
        # ----------------------------------------------

        try:

            warnings = skill.validate_step(
                step,
            )

            if warnings:

                logger.warning(
                    "Validación Skill warning=%s skill=%s",
                    warnings,
                    skill.name,
                )

        except Exception as exc:

            logger.exception(
                "Error validando skill=%s",
                skill.name,
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=f"skill:{skill.name}",
                plan_id=plan.id,
            )

        retries = 0

        max_retries = step.retries if step.retries is not None else plan.max_retries

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

                duration = round(
                    time.time() - start,
                    3,
                )

                self.metrics["duration"] += duration
                self.metrics["success"] += 1

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

                    duration = round(
                        time.time() - start,
                        3,
                    )

                    self.metrics["duration"] += duration
                    self.metrics["failed"] += 1

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
    # Normalization
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

                return {
                    "ok": bool(result["ok"]),
                    "result": result.get(
                        "result",
                        result,
                    ),
                    "error": result.get(
                        "error",
                    ),
                }

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

    # ======================================================
    # Metrics
    # ======================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
