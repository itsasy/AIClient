from __future__ import annotations

import logging

from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.execution_result import ExecutionResult

from runtime.registry.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime encargado de ejecutar Agents.

    Responsabilidades:

    - Resolver Agent desde registry.
    - Validar ejecución.
    - Ejecutar process().
    - Normalizar resultado.

    No:

    - Decide qué Agent usar.
    - Crea planes estratégicos.
    - Gestiona contexto.
    - Gestiona memoria.
    """

    name = "agent_runtime"

    def __init__(
        self,
        registry: AgentRegistry,
    ) -> None:

        self.registry = registry

    # ==================================================
    # Public API
    # ==================================================

    def execute(
        self,
        agent_name: str,
        params: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        params = dict(
            params or {},
        )

        plan = params.pop(
            "plan",
            None,
        )

        step = params.pop(
            "step",
            None,
        )

        context = params.pop(
            "context",
            {},
        )

        if not isinstance(
            plan,
            ExecutionPlan,
        ):

            plan = ExecutionPlan(
                original_task=params.get(
                    "task",
                    "",
                ),
                execution_unit_type="agent",
                execution_unit=agent_name,
            )

        try:

            agent = self.registry.get(
                agent_name,
            )

            if not agent:

                return ExecutionResult.fail(
                    error=f"Agent no encontrado: {agent_name}",
                    executor=self.name,
                )

            validation = agent.validate_plan(
                plan,
            )

            if validation:

                return ExecutionResult.fail(
                    error="; ".join(validation),
                    executor=self.name,
                )

            if not isinstance(
                step,
                ExecutionStep,
            ):

                step = ExecutionStep(
                    description=agent.name,
                    unit_type="agent",
                    unit_name=agent.name,
                    params=params,
                )

            result = agent.process(
                plan,
                step,
                {
                    **context,
                    **params,
                },
            )

            return ExecutionResult.success(
                result=result,
                executor=agent.name,
                metadata={
                    "runtime": self.name,
                    "agent": agent.name,
                },
            )

        except Exception as exc:

            logger.exception(
                "Error ejecutando agent=%s",
                agent_name,
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=self.name,
            )

    # ==================================================
    # Information
    # ==================================================

    def available_agents(
        self,
    ) -> list[str]:

        return self.registry.list()
