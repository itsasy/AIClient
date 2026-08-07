from __future__ import annotations

import logging
import time

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.execution_result import ExecutionResult

from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class SkillRuntime:

    name = "skill_runtime"

    def __init__(
        self,
        skill_manager: SkillManager | None = None,
    ):

        self.skill_manager = skill_manager or SkillManager()

    # ==================================================
    # Public API
    # ==================================================

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

            error = f"Skill no encontrada: " f"{step.unit_name}"

            step.mark_failed(
                error,
            )

            return self._fail_result(
                error,
                plan,
                step,
            )

        errors = step.validate()

        if errors:

            error = "; ".join(errors)

            step.mark_failed(
                error,
            )

            return self._fail_result(
                error,
                plan,
                step,
                skill,
            )

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

            return self._fail_result(
                error,
                plan,
                step,
                skill,
            )

        retries = step.retries if step.retries is not None else plan.max_retries

        attempts = 0

        start = time.time()

        while attempts <= retries:

            try:

                attempts += 1

                step.mark_running()

                logger.info(
                    "Ejecutando skill=%s step=%s intento=%s",
                    skill.name,
                    step.id,
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

                if not normalized.get(
                    "ok",
                    False,
                ):

                    raise RuntimeError(
                        normalized.get(
                            "error",
                        )
                        or "Skill falló"
                    )

                output = normalized.get(
                    "result",
                    result,
                )

                duration = round(
                    time.time() - start,
                    3,
                )

                step.mark_completed(
                    output,
                )

                step.metadata.update(
                    {
                        "skill": skill.name,
                        "attempts": attempts,
                        "duration": duration,
                    }
                )

                execution_result = ExecutionResult.ok(
                    output=output,
                    executor=f"skill:{skill.name}",
                    plan_id=plan.id,
                )

                execution_result.metadata.update(
                    {
                        "skill": skill.name,
                        "attempts": attempts,
                        "step_id": step.id,
                        "duration": duration,
                    }
                )

                return execution_result

            except Exception as exc:

                logger.warning(
                    "Skill falló %s intento=%s error=%s",
                    skill.name,
                    attempts,
                    exc,
                )

                if attempts > retries:

                    error = str(exc)

                    step.mark_failed(
                        error,
                    )

                    result = self._fail_result(
                        error,
                        plan,
                        step,
                        skill,
                        attempts,
                    )

                    result.metadata.update(
                        {
                            "duration": round(
                                time.time() - start,
                                3,
                            ),
                        }
                    )

                    return result

        return self._fail_result(
            "Max retries alcanzado",
            plan,
            step,
            skill,
            attempts,
        )

    # ==================================================
    # Error handling
    # ==================================================

    def _fail_result(
        self,
        error: str,
        plan: ExecutionPlan,
        step: ExecutionStep,
        skill=None,
        attempts: int | None = None,
    ) -> ExecutionResult:

        executor = self.name

        if skill:

            executor = f"skill:{skill.name}"

        result = ExecutionResult.fail(
            error=error,
            executor=executor,
            plan_id=plan.id,
        )

        result.metadata.update(
            {
                "step_id": step.id,
            }
        )

        if skill:

            result.metadata["skill"] = skill.name

        if attempts is not None:

            result.metadata["attempts"] = attempts

        return result

    # ==================================================
    # Result normalization
    # ==================================================

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
