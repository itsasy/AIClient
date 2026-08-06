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
    Router central de ejecución.

    Responsabilidad única:

    - Determinar qué runtime debe ejecutar.
    - Delegar ejecución.
    - Consolidar resultados.

    No:

    - Ejecuta agentes.
    - Ejecuta skills.
    - Construye contexto.
    - Modifica planificación.
    - Decide estrategia.
    """

    name = "execution_runtime"

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
        agent_runtime: AgentRuntime | None = None,
        skill_runtime: SkillRuntime | None = None,
    ):

        self.agent_manager = agent_manager or AgentManager()

        self.agent_runtime = agent_runtime or AgentRuntime()

        self.skill_runtime = skill_runtime or SkillRuntime()

    # ======================================================
    # Public API
    # ======================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:

        if plan.steps:

            return self._execute_steps(
                plan,
                context,
            )

        return self._execute_single(
            plan,
            context,
        )

    # ======================================================
    # Single execution
    # ======================================================

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

    # ======================================================
    # Multi step
    # ======================================================

    def _execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> ExecutionResult:

        outputs = []

        for step in plan.steps:

            result = self._dispatch(
                plan,
                step,
                context,
            )

            outputs.append(
                result.to_dict(),
            )

            if not result.success:

                if plan.stop_on_error:

                    return result

        return ExecutionResult.ok(
            output=outputs,
            executor=self.name,
            plan_id=plan.id,
        )

    # ======================================================
    # Router
    # ======================================================

    def _dispatch(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        unit_type = step.unit_type

        if unit_type == "agent":

            return self._execute_agent(
                plan,
                step,
                context,
            )

        if unit_type == "skill":

            return self.skill_runtime.execute(
                plan,
                step,
                context,
            )

        return ExecutionResult.fail(
            error=(f"Tipo de unidad inválido: {unit_type}"),
            executor=self.name,
            plan_id=plan.id,
        )

    # ======================================================
    # Agent dispatch
    # ======================================================

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

            return ExecutionResult.fail(
                error=(f"Agent no encontrado: " f"{step.unit_name}"),
                executor=self.name,
                plan_id=plan.id,
            )

        return self.agent_runtime.execute(
            plan,
            context,
            agent,
        )
