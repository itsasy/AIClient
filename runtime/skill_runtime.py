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
    - Validar ExecutionStep.
    - Ejecutar Skill.execute().
    - Gestionar retries.
    - Actualizar lifecycle del step.
    - Normalizar resultados.

    No:

    - Planifica.
    - Decide Skills.
    - Construye contexto.
    - Gestiona memoria.
    - Gestiona aprendizaje.
    - Gestiona métricas globales.
    """

    name = "skill_runtime"

    def __init__(
        self,
        skill_manager: SkillManager | None = None,
    ):

        self.skill_manager = skill_manager or SkillManager()

    # ==================================================
    # Execution
    # ==================================================

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        context = context or {}

        # --------------------------------------------------
        # Resolve Skill
        # --------------------------------------------------

        skill = self.skill_manager.get(
            step.unit_name,
        )

        if skill is None:

            error = f"Skill no encontrada: {step.unit_name}"

            step.mark_failed(
                error,
            )

            return ExecutionResult.fail(
                error=error,
                executor=self.name,
                plan_id=plan.id,
            )

        # --------------------------------------------------
        # Step validation
        # --------------------------------------------------

        errors = step.validate()

        if errors:

            error = "; ".join(errors)

            step.mark_failed(
                error,
            )

            return ExecutionResult.fail(
                error=error,
                executor=f"skill:{skill.name}",
                plan_id=plan.id,
            )

        # --------------------------------------------------
        # Skill validation
        # --------------------------------------------------

        try:

            warnings = skill.validate_step(
                step,
            )

            if warnings:

                step.metadata["warnings"] = warnings

        except Exception as exc:

            error = str(exc)

            step.mark_failed(
                error,
            )

            return ExecutionResult.fail(
                error=error,
                executor=f"skill:{skill.name}",
                plan_id=plan.id,
            )

        # --------------------------------------------------
        # Execution with retries
        # --------------------------------------------------

        max_retries = step.retries if step.retries is not None else plan.max_retries

        attempts = 0

        start = time.time()

        while attempts <= max_retries:

            try:

                step.mark_running()

                attempts += 1

                logger.info(
                    "Ejecutando skill=%s intento=%s",
                    skill.name,
                    attempts,
                )

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

                duration = round(
                    time.time() - start,
                    3,
                )

                output = normalized.get(
                    "result",
                    result,
                )

                step.mark_completed(
                    output,
                )

                step.metadata.update(
                    {
                        "duration": duration,
                        "skill": skill.name,
                        "attempts": attempts,
                    }
                )

                execution_result = ExecutionResult.ok(
                    output=output,
                    executor=f"skill:{skill.name}",
                    plan_id=plan.id,
                )

                execution_result.metadata.update(
                    {
                        "duration": duration,
                        "skill": skill.name,
                        "step_id": step.id,
                        "attempts": attempts,
                    }
                )

                return execution_result

            except Exception as exc:

                logger.warning(
                    "Skill falló skill=%s intento=%s error=%s",
                    skill.name,
                    attempts,
                    exc,
                )

                if attempts > max_retries:

                    error = str(exc)

                    step.mark_failed(
                        error,
                    )

                    return ExecutionResult.fail(
                        error=error,
                        executor=f"skill:{skill.name}",
                        plan_id=plan.id,
                    )

        return ExecutionResult.fail(
            error="Max retries alcanzado.",
            executor=f"skill:{skill.name}",
            plan_id=plan.id,
        )

    # ==================================================
    # Normalization
    # ==================================================

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
