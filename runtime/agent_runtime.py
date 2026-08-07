from __future__ import annotations

import logging
import time

from typing import Any

from agents.manager import AgentManager

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

    - Resolver Agent.
    - Validar ExecutionStep.
    - Validar Agent.
    - Ejecutar Agent.process().
    - Gestionar lifecycle del step.
    - Normalizar resultados.

    No:

    - Construye contexto.
    - Ejecuta Skills.
    - Decide workflows.
    """

    name = "agent_runtime"

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
    ):

        self.agent_manager = agent_manager or AgentManager()

    # ==================================================
    # Public API
    # ==================================================

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        context = context or {}

        agent = self.agent_manager.resolve(
            step.unit_name,
        )

        if agent is None:

            error = f"Agent no encontrado: " f"{step.unit_name}"

            step.mark_failed(
                error,
            )

            return self._fail_result(
                error,
                plan,
                step,
            )

        errors = step.validate()

        if errors:

            error = "; ".join(errors)

            step.mark_failed(
                error,
            )

            return self._fail_result(
                error,
                plan,
                step,
                agent,
            )

        try:

            warnings = agent.validate_plan(
                plan,
            )

            if warnings:

                step.metadata["warnings"] = warnings

        except Exception as exc:

            error = str(exc)

            step.mark_failed(
                error,
            )

            return self._fail_result(
                error,
                plan,
                step,
                agent,
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

            normalized = self._normalize_result(
                result,
            )

            if not normalized.get(
                "ok",
                False,
            ):

                raise RuntimeError(
                    normalized.get(
                        "error",
                    )
                    or "Agent falló"
                )

            output = normalized.get(
                "result",
                result,
            )

            duration = round(
                time.time() - start,
                3,
            )

            step.mark_completed(
                output,
            )

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

            duration = round(
                time.time() - start,
                3,
            )

            error = str(exc)

            step.mark_failed(
                error,
            )

            logger.exception(
                "Error ejecutando Agent=%s",
                agent.name,
            )

            result = self._fail_result(
                error,
                plan,
                step,
                agent,
            )

            result.metadata.update(
                {
                    "duration": duration,
                }
            )

            return result

    # ==================================================
    # Error handling
    # ==================================================

    def _fail_result(
        self,
        error: str,
        plan: ExecutionPlan,
        step: ExecutionStep,
        agent=None,
    ) -> ExecutionResult:

        executor = self.name

        if agent:

            executor = f"agent:{agent.name}"

        result = ExecutionResult.fail(
            error=error,
            executor=executor,
            plan_id=plan.id,
        )

        result.metadata.update(
            {
                "step_id": step.id,
            }
        )

        if agent:

            result.metadata["agent"] = agent.name

        return result

    # ==================================================
    # Result normalization
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
