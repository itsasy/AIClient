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

    - Recibir un Agent resuelto.
    - Ejecutar agent.process().
    - Validar compatibilidad del plan.
    - Normalizar resultados.

    No:

    - Selecciona agentes.
    - Construye contexto.
    - Cambia lifecycle del plan.
    - Ejecuta skills.
    """

    name = "agent_runtime"

    # ======================================================
    # Execution
    # ======================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        agent: Agent | None = None,
    ) -> ExecutionResult:

        if agent is None:

            return ExecutionResult.fail(
                error="AgentRuntime requiere un Agent.",
                executor=self.name,
                plan_id=plan.id,
            )

        logger.info(
            "Ejecutando agent=%s plan=%s",
            agent.name,
            plan.id,
        )

        # ----------------------------------------------
        # Agent validation
        # ----------------------------------------------

        try:

            validation_errors = agent.validate_plan(plan)

            if validation_errors:

                logger.warning(
                    "Plan incompatible con agent=%s errors=%s",
                    agent.name,
                    validation_errors,
                )

                return ExecutionResult.fail(
                    error=str(validation_errors),
                    executor=f"agent:{agent.name}",
                    plan_id=plan.id,
                )

        except Exception as exc:

            logger.exception(
                "Error validando agent=%s",
                agent.name,
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

        # ----------------------------------------------
        # Execution
        # ----------------------------------------------

        try:

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
