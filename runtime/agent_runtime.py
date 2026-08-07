from __future__ import annotations

import logging
import time

from typing import Any

from agents.base import Agent

from core.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)

from core.execution_result import ExecutionResult

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime encargado de ejecutar Agents.

    Responsabilidades:

    - Resolver ejecución de Agent recibido.
    - Validar compatibilidad del plan.
    - Ejecutar Agent.process().
    - Gestionar lifecycle del step.
    - Normalizar resultados.

    No:

    - Selecciona agentes.
    - Construye contexto.
    - Ejecuta Skills.
    - Modifica planificación.
    """

    name = "agent_runtime"

    def __init__(self):

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
            "duration": 0,
        }

    # ======================================================
    # Execution
    # ======================================================

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
        agent: Agent | None = None,
    ) -> ExecutionResult:

        start = time.time()

        self.metrics["executions"] += 1

        context = context or {}

        if agent is None:

            return ExecutionResult.fail(
                error="AgentRuntime requiere un Agent.",
                executor=self.name,
                plan_id=plan.id,
            )

        if step.unit_type != "agent":

            return ExecutionResult.fail(
                error=("AgentRuntime recibió " f"unit_type inválido: {step.unit_type}"),
                executor=self.name,
                plan_id=plan.id,
            )

        validation_errors = step.validate()

        if validation_errors:

            return ExecutionResult.fail(
                error=str(validation_errors),
                executor=self.name,
                plan_id=plan.id,
            )

        # ----------------------------------------------
        # Plan validation
        # ----------------------------------------------

        try:

            errors = agent.validate_plan(
                plan,
            )

            if errors:

                logger.warning(
                    "Plan rechazado por agent=%s errors=%s",
                    agent.name,
                    errors,
                )

                return ExecutionResult.fail(
                    error=str(errors),
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

        retries = 0

        max_retries = step.retries if step.retries is not None else plan.max_retries

        while retries <= max_retries:

            try:

                logger.info(
                    "Ejecutando agent=%s intento=%s",
                    agent.name,
                    retries + 1,
                )

                step.mark_running()

                result = agent.process(
                    plan,
                    context,
                )

                step.mark_completed(
                    result,
                )

                duration = round(
                    time.time() - start,
                    3,
                )

                self.metrics["duration"] += duration
                self.metrics["success"] += 1

                return ExecutionResult.ok(
                    output=result,
                    executor=f"agent:{agent.name}",
                    plan_id=plan.id,
                )

            except Exception as exc:

                retries += 1

                logger.exception(
                    "Error ejecutando agent=%s intento=%s",
                    agent.name,
                    retries,
                )

                if retries > max_retries:

                    step.mark_failed(
                        str(exc),
                    )

                    duration = round(
                        time.time() - start,
                        3,
                    )

                    self.metrics["duration"] += duration
                    self.metrics["failed"] += 1

                    return ExecutionResult.fail(
                        error=str(exc),
                        executor=f"agent:{agent.name}",
                        plan_id=plan.id,
                    )

        return ExecutionResult.fail(
            error="Max retries alcanzado.",
            executor=self.name,
            plan_id=plan.id,
        )

    # ======================================================
    # Metrics
    # ======================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
