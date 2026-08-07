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
    - Resolver modalidad single/multi_step.
    - Coordinar runtimes.
    - Gestionar lifecycle.
    - Generar ExecutionResult.

    No:

    - Detecta intención.
    - Construye planes.
    - Implementa agentes.
    - Implementa skills.
    - Gestiona memoria.
    """

    name = "execution_engine"

    def __init__(
        self,
        agent_runtime: AgentRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
        context_manager: ContextManager | None = None,
    ) -> None:

        self.agent_runtime = agent_runtime or AgentRuntime()

        self.skill_runtime = skill_runtime or SkillRuntime()

        self.context_manager = context_manager or ContextManager()

    # ==================================================
    # Public API
    # ==================================================

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        started = time.monotonic()

        try:

            self._validate_plan(
                plan,
            )

            plan.mark_running()

            self.context_manager.attach_to_plan(
                plan,
                {
                    "plan": plan,
                },
            )

            if plan.execution_mode == "single":

                result = self._execute_single(
                    plan,
                )

            else:

                result = self._execute_steps(
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

            if result.status == "completed":

                plan.mark_completed(
                    result.data,
                )

            elif result.status == "partial":

                plan.mark_partial(
                    result.data,
                    result.error,
                )

            else:

                plan.mark_failed(
                    result.error or "execution failed",
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
    # Single execution
    # ==================================================

    def _execute_single(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        if plan.execution_unit_type == "agent":

            return self.agent_runtime.execute(
                name=plan.execution_unit,
                params=plan.params,
                context=plan.execution_context,
            )

        if plan.execution_unit_type == "skill":

            return self.skill_runtime.execute(
                name=plan.execution_unit,
                params=plan.params,
                context=plan.execution_context,
            )

        raise ValueError(f"Unidad desconocida: {plan.execution_unit_type}")

    # ==================================================
    # Multi step execution
    # ==================================================

    def _execute_steps(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        outputs: list[Any] = []

        ordered_steps = self._resolve_order(
            plan.steps,
        )

        for step in ordered_steps:

            result = self._execute_step(
                step,
                plan,
            )

            outputs.append(
                result.data,
            )

            if result.status != "completed":

                if plan.stop_on_error:

                    return ExecutionResult.partial(
                        data=outputs,
                        error=result.error,
                        executor=self.name,
                    )

        return ExecutionResult.success(
            data=outputs,
            executor=self.name,
        )

    # ==================================================
    # Step execution
    # ==================================================

    def _execute_step(
        self,
        step: ExecutionStep,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        if step.unit_type == "agent":

            return self.agent_runtime.execute(
                name=step.unit_name,
                params=step.params,
                context=plan.execution_context,
            )

        if step.unit_type == "skill":

            return self.skill_runtime.execute(
                name=step.unit_name,
                params=step.params,
                context=plan.execution_context,
            )

        return ExecutionResult.fail(
            error=f"Tipo inválido: {step.unit_type}",
            executor=self.name,
        )

    # ==================================================
    # Validation
    # ==================================================

    def _validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> None:

        errors = plan.validate()

        if errors:

            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

    # ==================================================
    # Ordering
    # ==================================================

    def _resolve_order(
        self,
        steps: list[ExecutionStep],
    ) -> list[ExecutionStep]:

        resolved = []

        pending = list(
            steps,
        )

        completed = set()

        while pending:

            progress = False

            for step in pending[:]:

                dependencies = set(
                    step.depends_on,
                )

                if dependencies.issubset(
                    completed,
                ):

                    resolved.append(
                        step,
                    )

                    completed.add(
                        step.id,
                    )

                    pending.remove(
                        step,
                    )

                    progress = True

            if not progress:

                raise RuntimeError("Dependencias circulares en ExecutionPlan")

        return resolved
