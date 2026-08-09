from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from core.execution_step import ExecutionStep

from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class UnitDispatcher:
    """
    Resuelve y ejecuta una unidad del ExecutionPlan.

    Responsabilidades:
        - Resolver Agent o Skill.
        - Invocar su contrato de ejecución.
        - Normalizar errores de infraestructura de dispatch.

    No:
        - Decide qué unidad ejecutar.
        - Gestiona el lifecycle del plan.
        - Gestiona el lifecycle del step.
        - Construye contexto.
        - Ejecuta retries.
        - Evalúa resultados.
        - Hace learning.
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        skill_registry: SkillRegistry,
    ) -> None:
        self.agent_registry = agent_registry
        self.skill_registry = skill_registry

    # ==========================================================
    # Public API
    # ==========================================================

    def dispatch(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        unit_type = step.unit_type
        unit_name = step.unit_name

        if unit_type == "agent":
            return self._dispatch_agent(
                plan=plan,
                step=step,
                context=context,
            )

        if unit_type == "skill":
            return self._dispatch_skill(
                plan=plan,
                step=step,
                context=context,
            )

        return ExecutionResult.fail(
            plan_id=plan.id,
            error=f"Tipo de unidad inválido: {unit_type}",
            executor="dispatcher",
            metadata={
                "step_id": step.id,
                "unit_type": unit_type,
                "unit_name": unit_name,
            },
        )

    # ==========================================================
    # Agent
    # ==========================================================

    def _dispatch_agent(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        agent = self.agent_registry.get(
            step.unit_name,
        )

        if agent is None:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=f"Agent no encontrado: {step.unit_name}",
                executor="dispatcher",
                metadata={
                    "step_id": step.id,
                    "unit_type": "agent",
                    "unit_name": step.unit_name,
                },
            )

        try:
            result = agent.process(
                plan,
                step,
                context,
            )

            return ExecutionResult.success(
                plan_id=plan.id,
                result=result,
                executor=f"agent:{step.unit_name}",
                metadata={
                    "step_id": step.id,
                    "unit_type": "agent",
                    "unit_name": step.unit_name,
                },
            )

        except Exception as exc:
            logger.exception(
                "Error ejecutando Agent=%s",
                step.unit_name,
            )

            return ExecutionResult.fail(
                plan_id=plan.id,
                error=str(exc),
                executor=f"agent:{step.unit_name}",
                metadata={
                    "step_id": step.id,
                    "unit_type": "agent",
                    "unit_name": step.unit_name,
                },
            )

    # ==========================================================
    # Skill
    # ==========================================================

    def _dispatch_skill(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:

        skill = self.skill_registry.get(
            step.unit_name,
        )

        if skill is None:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=f"Skill no encontrada: {step.unit_name}",
                executor="dispatcher",
                metadata={
                    "step_id": step.id,
                    "unit_type": "skill",
                    "unit_name": step.unit_name,
                },
            )

        try:
            result = skill.execute(
                plan,
                step,
                context,
            )

            return ExecutionResult.success(
                plan_id=plan.id,
                result=result,
                executor=f"skill:{step.unit_name}",
                metadata={
                    "step_id": step.id,
                    "unit_type": "skill",
                    "unit_name": step.unit_name,
                },
            )

        except Exception as exc:
            logger.exception(
                "Error ejecutando Skill=%s",
                step.unit_name,
            )

            return ExecutionResult.fail(
                plan_id=plan.id,
                error=str(exc),
                executor=f"skill:{step.unit_name}",
                metadata={
                    "step_id": step.id,
                    "unit_type": "skill",
                    "unit_name": step.unit_name,
                },
            )
