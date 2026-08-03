from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.manager import AgentManager

from core.execution_plan import ExecutionPlan, ExecutionStep

logger = logging.getLogger(__name__)


class AgentRuntime:
    """
    Runtime encargado de ejecutar Agents.

    Flujo:

        ExecutionPlan
              |
              v
        AgentRuntime
              |
              v
        AgentManager
              |
              v
        Agent
              |
              v
        Resultado


    Responsabilidades:

    - Resolver agente mediante AgentManager.
    - Ejecutar agentes.
    - Ejecutar steps delegados.
    - Validar ejecución.
    - Capturar métricas.


    No:

    - Construye ExecutionPlan.
    - Analiza intención.
    - Construye contexto.
    - Ejecuta Skills directamente.
    """

    def __init__(
        self,
        agent_manager: AgentManager | None = None,
    ):

        self.manager = agent_manager or AgentManager()

        self.metrics = {
            "executions": 0,
            "completed": 0,
            "failed": 0,
        }

    # ==========================================================
    # Public API
    # ==========================================================

    def execute(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> Any:

        context = context or {}

        self.metrics["executions"] += 1

        logger.info(
            "AgentRuntime execute | agent=%s intent=%s",
            plan.agent,
            plan.intent,
        )

        try:

            validation_errors = plan.validate()

            if validation_errors:

                logger.warning(
                    "ExecutionPlan warnings: %s",
                    validation_errors,
                )

            result = self.manager.delegate(
                plan=plan,
                context=context,
            )

            self.metrics["completed"] += 1

            return result

        except Exception as exc:

            self.metrics["failed"] += 1

            logger.exception(
                "Error ejecutando agent runtime: %s",
                exc,
            )

            raise

    # ==========================================================
    # Multi step execution
    # ==========================================================

    def execute_steps(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        context = context or {}

        results = []

        for step in plan.steps:

            try:

                result = self.execute_step(
                    plan,
                    step,
                    context,
                )

                step.mark_completed(
                    result,
                )

                results.append(
                    {
                        "step": step.description,
                        "ok": True,
                        "result": result,
                    }
                )

            except Exception as exc:

                step.mark_failed(
                    str(exc),
                )

                results.append(
                    {
                        "step": step.description,
                        "ok": False,
                        "error": str(exc),
                    }
                )

                if plan.stop_on_error:

                    break

        return results

    # ==========================================================
    # Single step
    # ==========================================================

    def execute_step(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> Any:

        context = context or {}

        logger.info(
            "Executing step=%s skill=%s",
            step.description,
            step.skill,
        )

        step_plan = self._build_step_plan(
            plan,
            step,
        )

        return self.execute(
            step_plan,
            context,
        )

    # ==========================================================
    # Step plan creation
    # ==========================================================

    def _build_step_plan(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
    ) -> ExecutionPlan:

        step_plan = ExecutionPlan(
            original_task=step.description,
        )

        step_plan.intent = plan.intent

        step_plan.intent_category = plan.intent_category

        step_plan.agent = step.metadata.get("agent") or plan.agent

        step_plan.execution_mode = "single"

        step_plan.priority = plan.priority

        step_plan.skills = []

        if step.skill:

            step_plan.add_skill(
                step.skill,
            )

        step_plan.params.update(
            plan.params,
        )

        step_plan.params.update(
            step.params,
        )

        step_plan.context_requirements.extend(
            plan.context_requirements,
        )

        step_plan.execution_context.update(
            plan.execution_context,
        )

        step_plan.metadata.update(
            plan.metadata,
        )

        step_plan.metadata.update(
            step.metadata,
        )

        return step_plan

    # ==========================================================
    # Agent access
    # ==========================================================

    def get_agent(
        self,
        name: str,
    ) -> Agent | None:

        return self.manager.get(
            name,
        )

    def list_agents(
        self,
    ) -> list[str]:

        return self.manager.list_agents()

    def loaded_agents(
        self,
    ) -> list[str]:

        return self.manager.loaded_agents()

    # ==========================================================
    # Metrics
    # ==========================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
