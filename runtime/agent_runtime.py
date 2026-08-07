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

    - Validar ExecutionStep.
    - Validar Agent.
    - Ejecutar Agent.process().
    - Gestionar lifecycle del step.
    - Normalizar resultados.

    No:

    - Resuelve Agents.
    - Construye contexto.
    - Ejecuta Skills.
    - Decide workflows.
    """

    name = "agent_runtime"

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
        agent: Agent | None = None,
    ) -> ExecutionResult:

        context = context or {}

        if agent is None:

            error = "AgentRuntime requiere Agent."

            step.mark_failed(error)

            return ExecutionResult.fail(
                error=error,
                executor=self.name,
                plan_id=plan.id,
            )

        errors = step.validate()

        if errors:

            error = "; ".join(errors)

            step.mark_failed(error)

            return ExecutionResult.fail(
                error=error,
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

        try:

            warnings = agent.validate_plan(plan)

            if warnings:

                step.metadata["warnings"] = warnings

        except Exception as exc:

            error = str(exc)

            step.mark_failed(error)

            return ExecutionResult.fail(
                error=error,
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

        start = time.time()

        try:

            step.mark_running()

            logger.info(
                "Ejecutando agent=%s step=%s",
                agent.name,
                step.id,
            )

            result = agent.process(
                plan=plan,
                step=step,
                context=context,
            )

            normalized = self._normalize_result(result)

            if not normalized["ok"]:

                raise RuntimeError(
                    normalized.get(
                        "error",
                        "Agent falló",
                    )
                )

            output = normalized.get(
                "result",
                result,
            )

            duration = round(
                time.time() - start,
                3,
            )

            step.mark_completed(output)

            step.metadata.update(
                {
                    "agent": agent.name,
                    "duration": duration,
                }
            )

            execution_result = ExecutionResult.ok(
                output=output,
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

            execution_result.metadata.update(
                {
                    "agent": agent.name,
                    "step_id": step.id,
                    "duration": duration,
                }
            )

            return execution_result

        except Exception as exc:

            error = str(exc)

            step.mark_failed(error)

            logger.exception(
                "Error ejecutando Agent=%s",
                agent.name,
            )

            return ExecutionResult.fail(
                error=error,
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

    def _normalize_result(
        self,
        result: Any,
    ) -> dict[str, Any]:

        if isinstance(result, dict):

            if "ok" in result:

                return result

            return {
                "ok": True,
                "result": result,
                "error": None,
            }

        return {
            "ok": True,
            "result": result,
            "error": None,
        }
