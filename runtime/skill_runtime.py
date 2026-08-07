from __future__ import annotations

import logging
import time

from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FutureTimeoutError,
)

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
    - Ejecutar Skills.
    - Gestionar timeout.
    - Gestionar retries.
    - Normalizar resultados.
    - Registrar metadata.

    No:

    - Construye planes.
    - Decide Skills.
    - Gestiona contexto global.
    - Modifica ExecutionPlan.
    - Ejecuta Agents.
    """

    name = "skill_runtime"

    def __init__(
        self,
        skill_manager: SkillManager | None = None,
    ) -> None:

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

        validation_errors = step.validate()

        if validation_errors:

            return self._fail(
                plan,
                step,
                "; ".join(validation_errors),
            )

        skill = self.skill_manager.get(
            step.unit_name,
        )

        if skill is None:

            return self._fail(
                plan,
                step,
                f"Skill no encontrada: {step.unit_name}",
            )

        try:

            warnings = skill.validate_step(
                step,
            )

            if warnings:

                step.metadata["warnings"] = warnings

        except Exception as exc:

            return self._fail(
                plan,
                step,
                f"Error validando Skill: {exc}",
            )

        retries = step.retries if step.retries is not None else plan.max_retries

        attempts = 0

        started = time.monotonic()

        while attempts <= retries:

            attempts += 1

            try:

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
                    step.timeout,
                )

                result = self._normalize_result(
                    raw_result,
                    plan,
                    skill.name,
                )

                if result.status != "completed":

                    raise RuntimeError(
                        result.error or "Skill falló",
                    )

                duration = round(
                    time.monotonic() - started,
                    3,
                )

                result.metadata.update(
                    {
                        "skill": skill.name,
                        "step_id": step.id,
                        "attempts": attempts,
                        "duration": duration,
                    }
                )

                return result

            except Exception as exc:

                logger.warning(
                    "Error ejecutando skill=%s intento=%s error=%s",
                    skill.name,
                    attempts,
                    exc,
                )

                if attempts > retries:

                    return self._fail(
                        plan,
                        step,
                        str(exc),
                        skill.name,
                        attempts,
                        started,
                    )

                self._retry_wait(
                    attempts,
                )

        return self._fail(
            plan,
            step,
            "Max retries alcanzado",
            skill.name,
            attempts,
            started,
        )

    # ==================================================
    # Execution
    # ==================================================

    def _execute_with_timeout(
        self,
        func: Callable[[], Any],
        timeout: int | None,
    ) -> Any:

        if not timeout:

            return func()

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

                raise TimeoutError(
                    f"Skill excedió timeout de {timeout}s",
                )

    # ==================================================
    # Result normalization
    # ==================================================

    def _normalize_result(
        self,
        result: Any,
        plan: ExecutionPlan,
        skill_name: str,
    ) -> ExecutionResult:

        if isinstance(
            result,
            ExecutionResult,
        ):

            return result

        return ExecutionResult.ok(
            output=result,
            executor=f"skill:{skill_name}",
            plan_id=plan.id,
        )

    # ==================================================
    # Error handling
    # ==================================================

    def _fail(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        error: str,
        skill_name: str | None = None,
        attempts: int | None = None,
        started: float | None = None,
    ) -> ExecutionResult:

        result = ExecutionResult.fail(
            error=error,
            executor=(f"skill:{skill_name}" if skill_name else self.name),
            plan_id=plan.id,
        )

        result.metadata.update(
            {
                "step_id": step.id,
                "skill": skill_name or step.unit_name,
            }
        )

        if attempts is not None:

            result.metadata["attempts"] = attempts

        if started is not None:

            result.metadata["duration"] = round(
                time.monotonic() - started,
                3,
            )

        return result

    # ==================================================
    # Retry
    # ==================================================

    def _retry_wait(
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
