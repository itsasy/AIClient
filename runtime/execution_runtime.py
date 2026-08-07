from __future__ import annotations

import logging

from typing import Any

from agents.manager import AgentManager
from skills.manager import SkillManager

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
    - Delegar Agent/Skill runtime.
    - Ordenar steps.
    - Consolidar resultados.

    No:

    - Ejecuta Agents.
    - Ejecuta Skills.
    - Construye contexto.
    - Modifica planes.
    """

    name = "execution_runtime"

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
        skill_manager: SkillManager | None = None,
        agent_runtime: AgentRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
    ):

        self.agent_manager = agent_manager or AgentManager()

        self.skill_manager = skill_manager or SkillManager()

        self.agent_runtime = agent_runtime or AgentRuntime()

        self.skill_runtime = skill_runtime or SkillRuntime(
            self.skill_manager,
        )

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
    # Single
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
            unit_type=plan.execution_unit_type,
            unit_name=plan.execution_unit,
            params=plan.params,
        )

        return self._dispatch(
            plan,
            step,
            context,
        )

    # ==================================================
    # Multi step
    # ==================================================

    def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:

        outputs = []

        for step in self._resolve_execution_order(
            plan.steps,
        ):

            result = self._dispatch(
                plan,
                step,
                context,
            )

            outputs.append(
                result.to_dict(),
            )

            if not result.success and plan.stop_on_error:

                return result

        return ExecutionResult.ok(
            output=outputs,
            executor=self.name,
            plan_id=plan.id,
        )

    # ==================================================
    # Dependencies
    # ==================================================

    def _resolve_execution_order(
        self,
        steps: list[ExecutionStep],
    ) -> list[ExecutionStep]:

        completed = set()
        ordered = []
        pending = steps.copy()

        while pending:

            progress = False

            for step in pending[:]:

                if all(dependency in completed for dependency in step.depends_on):

                    ordered.append(step)

                    completed.add(
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
    # Router
    # ==================================================

    def _dispatch(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        if step.unit_type == "agent":

            return self._execute_agent(
                plan,
                step,
                context,
            )

        if step.unit_type == "skill":

            return self.skill_runtime.execute(
                plan,
                step,
                context,
            )

        return ExecutionResult.fail(
            error=f"Tipo de unidad inválido: {step.unit_type}",
            executor=self.name,
            plan_id=plan.id,
        )

    # ==================================================
    # Agent
    # ==================================================

    def _execute_agent(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        agent = self.agent_manager.get(
            step.unit_name,
        )

        if agent is None:

            step.mark_failed(f"Agent no encontrado: {step.unit_name}")

            return ExecutionResult.fail(
                error=f"Agent no encontrado: {step.unit_name}",
                executor=self.name,
                plan_id=plan.id,
            )

        return self.agent_runtime.execute(
            plan=plan,
            step=step,
            context=context,
            agent=agent,
        )
