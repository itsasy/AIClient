from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from core.execution_result import ExecutionResult

from agents.manager import AgentManager

from runtime.agent_runtime import AgentRuntime
from runtime.skill_runtime import SkillRuntime

logger = logging.getLogger(__name__)


class ExecutionRuntime:
    """
    Runtime unificado.

    Ejecuta:
    - Agents
    - Skills
    - Steps completos
    """

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
        agent_runtime: AgentRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
    ):

        self.agent_manager = agent_manager or AgentManager()

        self.agent_runtime = agent_runtime or AgentRuntime()

        self.skill_runtime = skill_runtime or SkillRuntime()

    # ==========================================================
    # Public execution
    # ==========================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:

        if plan.steps:

            return self.execute_steps(
                plan,
                context,
            )

        return self.execute_unit(
            plan.execution_unit_type,
            plan,
            None,
            context,
        )

    # ==========================================================
    # Steps execution
    # ==========================================================

    def execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:

        results = []

        for step in plan.steps:

            result = self.execute_unit(
                step.unit_type,
                plan,
                step,
                context,
            )

            results.append(result.to_dict())

            if not result.success and plan.stop_on_error:

                return result

        return ExecutionResult.ok(
            output=results,
            executor="execution_runtime",
            plan_id=plan.id,
        )

    # ==========================================================
    # Unit execution
    # ==========================================================

    def execute_unit(
        self,
        unit_type: str | None,
        plan: ExecutionPlan,
        step: ExecutionStep | None,
        context: dict[str, Any],
    ) -> ExecutionResult:

        if unit_type == "skill":

            if step is None:

                step = ExecutionStep(
                    description=plan.objective or plan.original_task,
                    unit_type="skill",
                    unit_name=plan.execution_unit,
                    params=plan.params,
                )

            return self.skill_runtime.execute(
                plan,
                step,
                context,
            )

        if unit_type == "agent":

            agent = self.agent_manager.get(plan.execution_unit)

            if agent is None:

                return ExecutionResult.fail(
                    error=f"Agent no encontrado: {plan.execution_unit}",
                    executor="execution_runtime",
                    plan_id=plan.id,
                )

            return self.agent_runtime.execute(
                plan,
                context,
                agent,
            )

        return ExecutionResult.fail(
            error=f"Unidad desconocida: {unit_type}",
            executor="execution_runtime",
            plan_id=plan.id,
        )
