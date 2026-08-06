from __future__ import annotations

import logging

from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan

from core.execution_result import ExecutionResult

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime encargado de ejecutar Agents.

    Responsabilidades:

    - Validar Agent.
    - Ejecutar process().
    - Normalizar salida.

    No:

    - Selecciona agentes.
    - Construye contexto.
    - Ejecuta skills.
    """

    name = "agent_runtime"

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        agent: Agent | None = None,
    ) -> ExecutionResult:

        if agent is None:

            return ExecutionResult.fail(
                error="AgentRuntime requiere Agent.",
                executor=self.name,
                plan_id=plan.id,
            )

        try:

            errors = agent.validate_plan(
                plan,
            )

            if errors:

                return ExecutionResult.fail(
                    error=str(errors),
                    executor=f"agent:{agent.name}",
                    plan_id=plan.id,
                )

            result = agent.process(
                plan,
                context,
            )

            return ExecutionResult.ok(
                output=result,
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

        except Exception as exc:

            logger.exception(
                "Error ejecutando agent=%s",
                agent.name,
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )
