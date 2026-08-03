from __future__ import annotations

import logging
from typing import Any

from agents.manager import AgentManager

from core.execution_plan import ExecutionPlan, ExecutionStep

from runtime.agent_runtime import AgentRuntime
from runtime.skill_runtime import SkillRuntime

logger = logging.getLogger(__name__)


class ExecutionRuntime:
    """
    Runtime unificado de ejecución.

    Responsabilidades:

    - Resolver unidad ejecutable.
    - Ejecutar Agents o Skills.
    - Mantener flujo único.
    - Normalizar resultados.

    No:

    - Crea ExecutionPlans.
    - Analiza intención.
    - Construye contexto.
    - Decide providers LLM.
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

    # ======================================================
    # Public execution
    # ======================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> Any:

        unit_type = self._resolve_unit_type(
            plan,
        )

        logger.info(
            "ExecutionRuntime unit=%s plan=%s",
            unit_type,
            plan.id,
        )

        if unit_type == "agent":

            return self._execute_agent(
                plan,
                context,
            )

        if unit_type == "skill":

            step = plan.current_step()

            if step is None:
                step = ExecutionStep(
                    description=plan.objective or plan.original_task,
                    skill=plan.skill,
                    params=plan.params,
                )
            return self.skill_runtime.execute(
                plan,
                step,
                context,
            )

        raise RuntimeError(f"Unidad de ejecución desconocida: {unit_type}")

    # ======================================================
    # Agent execution
    # ======================================================

    def _execute_agent(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> Any:

        agent = self.agent_manager._select(
            plan,
        )

        if agent is None:

            raise RuntimeError("No existe agente disponible.")

        return self.agent_runtime.execute(
            plan=plan,
            context=context,
            agent=agent,
        )

    # ======================================================
    # Resolution
    # ======================================================

    def _resolve_unit_type(
        self,
        plan: ExecutionPlan,
    ) -> str:

        metadata_type = plan.metadata.get(
            "unit_type",
        )

        if metadata_type:

            return metadata_type

        if plan.agent:

            return "agent"

        if plan.skill:

            return "skill"

        if plan.skills:

            return "skill"

        return "agent"
