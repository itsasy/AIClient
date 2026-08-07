from __future__ import annotations

import logging

from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from core.execution_result import ExecutionResult

from runtime.agent_runtime import AgentRuntime
from runtime.skill_runtime import SkillRuntime

logger = logging.getLogger(__name__)


class ExecutionRuntime:
    """
    Router central de ejecución.

    Responsabilidades:

    - Resolver tipo de ejecución.
    - Delegar a AgentRuntime.
    - Delegar a SkillRuntime.
    - Resolver orden de steps.
    - Consolidar resultados.

    No:

    - Ejecuta Agents.
    - Ejecuta Skills.
    - Construye contexto.
    - Gestiona memoria.
    - Gestiona aprendizaje.
    - Modifica planes.
    """

    name = "execution_runtime"

    def __init__(
        self,
        agent_runtime: AgentRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
    ):

        self.agent_runtime = agent_runtime or AgentRuntime()

        self.skill_runtime = skill_runtime or SkillRuntime()

    # ==================================================
    # Public API
    # ==================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        context = context or {}

        if plan.steps:

            return self._execute_steps(
                plan,
                context,
            )

        return self._execute_single(
            plan,
            context,
        )

    # ==================================================
    # Single execution
    # ==================================================

    def _execute_single(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:

        if not plan.execution_unit_type:

            return ExecutionResult.fail(
                error="Plan sin unidad de ejecución.",
                executor=self.name,
                plan_id=plan.id,
            )

        step = ExecutionStep(
            description=(plan.objective or plan.original_task),
            unit_type=ExecutionStep.normalize_unit_type(
                plan.execution_unit_type,
            ),
            unit_name=plan.execution_unit,
            params=plan.params,
        )

        return self._dispatch(
            plan,
            step,
            context,
        )

    # ==================================================
    # Multi step execution
    # ==================================================

    def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:

        children: list[ExecutionResult] = []

        failed_steps: list[str] = []

        completed_steps: list[str] = []

        ordered_steps = self._resolve_execution_order(
            plan.steps,
        )

        for step in ordered_steps:

            result = self._dispatch(
                plan,
                step,
                context,
            )

            children.append(
                result,
            )

            if result.is_success():

                completed_steps.append(
                    step.id,
                )

            else:

                failed_steps.append(
                    step.id,
                )

                if plan.stop_on_error:

                    break

        # ------------------------------------------
        # Todo correcto
        # ------------------------------------------

        if not failed_steps:

            return ExecutionResult.ok(
                output=[child.to_dict() for child in children],
                executor=self.name,
                plan_id=plan.id,
            ).with_metadata(
                steps=len(children),
            )

        # ------------------------------------------
        # Todo falló
        # ------------------------------------------

        if not completed_steps:

            return ExecutionResult.fail(
                error="Todos los steps fallaron.",
                executor=self.name,
                plan_id=plan.id,
            ).with_metadata(
                failed_steps=failed_steps,
                steps=len(children),
            )

        # ------------------------------------------
        # Ejecución parcial
        # ------------------------------------------

        return ExecutionResult.partial(
            output={
                "completed_steps": completed_steps,
                "failed_steps": failed_steps,
            },
            executor=self.name,
            plan_id=plan.id,
            children=children,
        ).with_metadata(
            steps=len(children),
            completed=len(completed_steps),
            failed=len(failed_steps),
        )

    # ==================================================
    # Dependency resolver
    # ==================================================

    def _resolve_execution_order(
        self,
        steps: list[ExecutionStep],
    ) -> list[ExecutionStep]:

        ordered: list[ExecutionStep] = []

        resolved: set[str] = set()

        pending = steps.copy()

        while pending:

            progress = False

            for step in pending[:]:

                ready = all(dependency in resolved for dependency in step.depends_on)

                if ready:

                    ordered.append(
                        step,
                    )

                    resolved.add(
                        step.id,
                    )

                    pending.remove(
                        step,
                    )

                    progress = True

            if not progress:

                raise RuntimeError("Dependencias circulares en ExecutionPlan.")

        return ordered

    # ==================================================
    # Dispatcher
    # ==================================================

    def _dispatch(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        unit_type = ExecutionStep.normalize_unit_type(
            step.unit_type,
        )

        if unit_type == "agent":

            return self.agent_runtime.execute(
                plan=plan,
                step=step,
                context=context,
            )

        if unit_type == "skill":

            return self.skill_runtime.execute(
                plan=plan,
                step=step,
                context=context,
            )

        error = f"Tipo de unidad inválido: " f"{unit_type}"

        step.mark_failed(
            error,
        )

        result = ExecutionResult.fail(
            error=error,
            executor=self.name,
            plan_id=plan.id,
        )

        result.metadata.update(
            {
                "step_id": step.id,
            }
        )

        return result
