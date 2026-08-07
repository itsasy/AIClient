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

            step.mark_failed("AgentRuntime requiere Agent.")

            return ExecutionResult.fail(
                error="AgentRuntime requiere Agent.",
                executor=self.name,
                plan_id=plan.id,
            )

        # ==================================================
        # Step validation
        # ==================================================

        errors = step.validate()

        if errors:

            step.mark_failed(
                str(errors),
            )

            return ExecutionResult.fail(
                error=str(errors),
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

        # ==================================================
        # Agent validation
        # ==================================================

        try:

            warnings = agent.validate_plan(
                plan,
            )

            if warnings:

                step.metadata["warnings"] = warnings

        except Exception as exc:

            step.mark_failed(
                str(exc),
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

        # ==================================================
        # Execution
        # ==================================================

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

            duration = round(
                time.time() - start,
                3,
            )

            normalized = self._normalize_result(
                result,
            )

            if not normalized["ok"]:

                raise RuntimeError(
                    normalized.get(
                        "error",
                        "Agent falló",
                    )
                )

            step.mark_completed(
                result,
            )

            step.metadata.update(
                {
                    "duration": duration,
                    "agent": agent.name,
                }
            )

            execution_result = ExecutionResult.ok(
                output=result,
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

            execution_result.metadata.update(
                {
                    "step_id": step.id,
                    "agent": agent.name,
                    "duration": duration,
                }
            )

            return execution_result

        except Exception as exc:

            step.mark_failed(
                str(exc),
            )

            logger.exception(
                "Error ejecutando Agent=%s",
                agent.name,
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

    # ==================================================
    # Normalization
    # ==================================================

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
