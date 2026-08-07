from __future__ import annotations

import logging
import time

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from typing import Any, Callable

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.execution_result import ExecutionResult

from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class SkillRuntime:
    """
    Runtime central de ejecución de Skills.

    Responsabilidades:

    - Resolver Skills.
    - Ejecutar Steps.
    - Gestionar retries.
    - Aplicar timeout.
    - Normalizar resultados.
    - Registrar metadata.

    No:

    - Contiene lógica de negocio.
    - Decide qué Skill usar.
    - Construye planes.
    """

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

            error = f"Skill no encontrada: {step.unit_name}"

            self._safe_mark_failed(
                step,
                error,
            )

            return self._fail_result(
                error,
                plan,
                step,
            )

        validation_errors = step.validate()

        if validation_errors:

            error = "; ".join(validation_errors)

            self._safe_mark_failed(
                step,
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

            error = f"Error validando skill: {exc}"

            self._safe_mark_failed(
                step,
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

        started = time.monotonic()

        while attempts <= retries:

            attempts += 1

            try:

                step.mark_running()

                logger.info(
                    "Ejecutando skill=%s step=%s intento=%s",
                    skill.name,
                    step.id,
                    attempts,
                )

                raw_result = self._execute_with_timeout(
                    lambda: skill.execute(
                        plan=plan,
                        step=step,
                        context=context,
                    ),
                    timeout=step.timeout,
                )

                result = self._normalize_result(
                    raw_result,
                )

                if not result["ok"]:

                    raise RuntimeError(result.get("error") or "Skill falló")

                output = result.get(
                    "result",
                )

                duration = round(
                    time.monotonic() - started,
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
                        "step_id": step.id,
                        "attempts": attempts,
                        "duration": duration,
                    }
                )

                return execution_result

            except TimeoutError as exc:

                logger.warning(
                    "Timeout Skill=%s intento=%s",
                    skill.name,
                    attempts,
                )

                if attempts > retries:

                    error = str(exc)

                    self._safe_mark_failed(
                        step,
                        error,
                    )

                    return self._fail_result(
                        error,
                        plan,
                        step,
                        skill,
                        attempts,
                    )

            except Exception as exc:

                logger.warning(
                    "Fallo Skill=%s intento=%s error=%s",
                    skill.name,
                    attempts,
                    exc,
                )

                if not self._is_retryable_error(exc):

                    error = str(exc)

                    self._safe_mark_failed(
                        step,
                        error,
                    )

                    return self._fail_result(
                        error,
                        plan,
                        step,
                        skill,
                        attempts,
                    )

                if attempts > retries:

                    error = str(exc)

                    self._safe_mark_failed(
                        step,
                        error,
                    )

                    return self._fail_result(
                        error,
                        plan,
                        step,
                        skill,
                        attempts,
                    )

            if attempts <= retries:

                self._wait_retry(
                    attempts,
                )

        return self._fail_result(
            "Max retries alcanzado",
            plan,
            step,
            skill,
            attempts,
        )

    # ==================================================
    # Execution helpers
    # ==================================================

    def _execute_with_timeout(
        self,
        func: Callable[[], Any],
        timeout: int,
    ) -> Any:

        with ThreadPoolExecutor(
            max_workers=1,
        ) as executor:

            future = executor.submit(
                func,
            )

            try:

                return future.result(
                    timeout=timeout,
                )

            except FutureTimeoutError:

                raise TimeoutError(f"Skill excedió timeout de {timeout}s")

    def _is_retryable_error(
        self,
        error: Exception,
    ) -> bool:

        non_retryable = (
            ValueError,
            TypeError,
            KeyError,
        )

        return not isinstance(
            error,
            non_retryable,
        )

    def _wait_retry(
        self,
        attempt: int,
    ) -> None:

        delay = min(
            attempt * 0.5,
            5,
        )

        time.sleep(
            delay,
        )

    # ==================================================
    # State helpers
    # ==================================================

    def _safe_mark_failed(
        self,
        step: ExecutionStep,
        error: str,
    ) -> None:

        try:

            step.mark_failed(
                error,
            )

        except Exception:

            logger.exception(
                "Error marcando step fallido",
            )

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

            return {
                "ok": result.get(
                    "ok",
                    True,
                ),
                "result": result.get(
                    "result",
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
