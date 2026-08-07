from __future__ import annotations

import logging
import time

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep

from core.context.manager import ContextManager

from runtime.agent_runtime import AgentRuntime
from runtime.skill_runtime import SkillRuntime

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Motor central de ejecución.

    Responsabilidades:

    - Ejecutar ExecutionPlans.
    - Resolver tipo de unidad.
    - Coordinar runtimes.
    - Controlar lifecycle básico.

    No:

    - Planifica.
    - Detecta intención.
    - Gestiona memoria.
    - Decide estrategia LLM.
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_runtime: AgentRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:

        self.agent_runtime = agent_runtime
        self.skill_runtime = skill_runtime
        self.context_manager = context_manager

    # ==================================================
    # Public API
    # ==================================================

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        started = time.monotonic()

        try:

            errors = plan.validate()

            if errors:

                return ExecutionResult.fail(
                    error=", ".join(errors),
                    executor=self.name,
                )

            if self.context_manager:

                self.context_manager.attach_to_plan(
                    plan,
                    request=plan.params,
                )

            plan.mark_running()

            if plan.execution_mode == "multi_step":

                result = self._execute_steps(
                    plan,
                )

            else:

                result = self._execute_single(
                    plan,
                )

            duration = round(
                time.monotonic() - started,
                3,
            )

            result.metadata.update(
                {
                    "engine": self.name,
                    "duration": duration,
                    "plan_id": plan.id,
                }
            )

            self._apply_result_state(
                plan,
                result,
            )

            return result

        except Exception as exc:

            logger.exception(
                "ExecutionEngine error",
            )

            try:

                plan.mark_failed(
                    str(exc),
                )

            except Exception:

                pass

            return ExecutionResult.fail(
                error=str(exc),
                executor=self.name,
            )

    # ==================================================
    # Result lifecycle
    # ==================================================

    def _apply_result_state(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:

        if result.status == "completed":

            plan.mark_completed(
                result.result,
            )

            return

        if result.status == "partial":

            plan.mark_partial(
                result=result.result,
                error=result.error,
            )

            return

        plan.mark_failed(
            result.error or "execution_failed",
        )

    # ==================================================
    # Single execution
    # ==================================================

    def _execute_single(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        if not plan.execution_unit_type:

            return ExecutionResult.fail(
                error="Plan sin execution_unit_type",
                executor=self.name,
            )

        params = self._build_runtime_params(
            plan.params,
            plan.execution_context,
        )

        if plan.execution_unit_type == "agent":

            if not self.agent_runtime:

                return ExecutionResult.fail(
                    error="AgentRuntime no configurado",
                    executor=self.name,
                )

            return self.agent_runtime.execute(
                agent_name=plan.execution_unit,
                params=params,
            )

        if plan.execution_unit_type == "skill":

            if not self.skill_runtime:

                return ExecutionResult.fail(
                    error="SkillRuntime no configurado",
                    executor=self.name,
                )

            return self.skill_runtime.execute(
                skill_name=plan.execution_unit,
                params=params,
            )

        return ExecutionResult.fail(
            error=f"Tipo de ejecución desconocido: {plan.execution_unit_type}",
            executor=self.name,
        )

    # ==================================================
    # Multi step
    # ==================================================

    def _execute_steps(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        outputs: list[Any] = []

        for step in plan.steps:

            result = self._execute_step(
                step,
                plan.execution_context,
            )

            outputs.append(
                result,
            )

            if result.status != "completed":

                if plan.stop_on_error:

                    return ExecutionResult.partial(
                        result=outputs,
                        error=result.error,
                        executor=self.name,
                    )

        return ExecutionResult.success(
            result=outputs,
            executor=self.name,
        )

    # ==================================================
    # Step execution
    # ==================================================

    def _execute_step(
        self,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        params = self._build_runtime_params(
            step.params,
            context,
        )

        if step.unit_type == "agent":

            if not self.agent_runtime:

                return ExecutionResult.fail(
                    error="AgentRuntime no configurado",
                    executor=self.name,
                )

            return self.agent_runtime.execute(
                agent_name=step.unit_name,
                params=params,
            )

        if step.unit_type == "skill":

            if not self.skill_runtime:

                return ExecutionResult.fail(
                    error="SkillRuntime no configurado",
                    executor=self.name,
                )

            return self.skill_runtime.execute(
                skill_name=step.unit_name,
                params=params,
            )

        return ExecutionResult.fail(
            error=f"Unidad inválida: {step.unit_type}",
            executor=self.name,
        )

    # ==================================================
    # Helpers
    # ==================================================

    @staticmethod
    def _build_runtime_params(
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:

        return {
            **params,
            "context": context,
        }
