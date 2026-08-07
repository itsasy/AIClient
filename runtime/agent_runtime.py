from __future__ import annotations

import logging
import time

from typing import Any

from agents.manager import AgentManager

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.execution_result import ExecutionResult

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime central de ejecución de Agents.

    Responsabilidades:

    - Resolver Agent.
    - Validar ExecutionStep.
    - Validar Agent.
    - Ejecutar Agent.process().
    - Gestionar lifecycle del step.
    - Normalizar resultados.
    - Registrar metadata.

    No:

    - Construye planes.
    - Ejecuta Skills.
    - Gestiona contexto global.
    - Gestiona memoria.
    - Gestiona aprendizaje.
    """

    name = "agent_runtime"

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
    ) -> None:

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

        validation_errors = step.validate()

        if validation_errors:

            return self._fail(
                plan,
                step,
                "; ".join(validation_errors),
            )

        if not step.unit_name:

            return self._fail(
                plan,
                step,
                "ExecutionStep sin Agent asignado.",
            )

        agent = self.agent_manager.resolve(
            step.unit_name,
        )

        if agent is None:

            return self._fail(
                plan,
                step,
                f"Agent no encontrado: {step.unit_name}",
            )

        try:

            warnings = agent.validate_plan(
                plan,
            )

            if warnings:

                step.metadata["warnings"] = warnings

        except Exception as exc:

            return self._fail(
                plan,
                step,
                f"Error validando Agent: {exc}",
                agent,
            )

        started = time.monotonic()

        try:

            step.mark_running()

            logger.info(
                "Ejecutando agent=%s step=%s",
                agent.name,
                step.id,
            )

            raw_result = agent.process(
                plan=plan,
                step=step,
                context=context,
            )

            result = self._normalize_result(
                raw_result,
                plan,
                agent,
            )

            if not result.is_success():

                raise RuntimeError(
                    result.error or "Agent falló",
                )

            duration = round(
                time.monotonic() - started,
                3,
            )

            step.mark_completed(
                result.output,
            )

            step.metadata.update(
                {
                    "agent": agent.name,
                    "duration": duration,
                }
            )

            result.metadata.update(
                {
                    "agent": agent.name,
                    "step_id": step.id,
                    "duration": duration,
                }
            )

            return result

        except Exception as exc:

            logger.exception(
                "Error ejecutando Agent=%s",
                agent.name,
            )

            return self._fail(
                plan,
                step,
                str(exc),
                agent,
            )

    # ==================================================
    # Error handling
    # ==================================================

    def _fail(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        error: str,
        agent: Any = None,
    ) -> ExecutionResult:

        try:

            step.mark_failed(
                error,
            )

        except Exception:

            logger.exception(
                "No se pudo marcar step fallido",
            )

        executor = self.name

        metadata = {
            "step_id": step.id,
            "agent": step.unit_name,
        }

        if agent:

            executor = f"agent:{agent.name}"

            metadata["agent"] = agent.name

        result = ExecutionResult.fail(
            error=error,
            executor=executor,
            plan_id=plan.id,
        )

        result.metadata.update(
            metadata,
        )

        return result

    # ==================================================
    # Result normalization
    # ==================================================

    def _normalize_result(
        self,
        result: Any,
        plan: ExecutionPlan,
        agent: Any,
    ) -> ExecutionResult:

        if isinstance(
            result,
            ExecutionResult,
        ):

            return result

        if isinstance(
            result,
            dict,
        ):

            if "ok" in result:

                if result.get("ok"):

                    return ExecutionResult.ok(
                        output=result.get("result"),
                        executor=f"agent:{agent.name}",
                        plan_id=plan.id,
                    )

                return ExecutionResult.fail(
                    error=result.get(
                        "error",
                    )
                    or "Agent falló",
                    executor=f"agent:{agent.name}",
                    plan_id=plan.id,
                )

            return ExecutionResult.ok(
                output=result,
                executor=f"agent:{agent.name}",
                plan_id=plan.id,
            )

        return ExecutionResult.ok(
            output=result,
            executor=f"agent:{agent.name}",
            plan_id=plan.id,
        )
