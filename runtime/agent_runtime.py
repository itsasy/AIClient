from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent

from core.execution_plan import ExecutionPlan

from core.execution_result import ExecutionResult

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime de ejecución de agentes.

    Responsabilidades:

    - Ejecutar un Agent.
    - Validar ExecutionPlan.
    - Gestionar lifecycle.
    - Normalizar errores.

    No:

    - Selecciona agentes.
    - Construye contexto.
    - Ejecuta skills.
    """

    name = "agent_runtime"

    # ==========================================================
    # Public execution
    # ==========================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
        agent: Agent | None = None,
    ) -> Any:

        if agent is None:

            raise RuntimeError("AgentRuntime requiere un Agent.")

        logger.info(
            "Ejecutando agent=%s plan=%s",
            agent.name,
            plan.id,
        )

        validation_errors = agent.validate_plan(
            plan,
        )

        if validation_errors:

            logger.warning(
                "Validación agent=%s errores=%s",
                agent.name,
                validation_errors,
            )

            plan.metadata.setdefault(
                "validation_warnings",
                [],
            ).extend(
                validation_errors,
            )

        try:

            plan.mark_running()

            result = agent.process(
                plan,
                context,
            )

            plan.mark_completed(
                result,
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

            plan.mark_failed(
                str(exc),
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )
