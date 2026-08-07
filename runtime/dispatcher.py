from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from core.execution_result import ExecutionResult

from runtime.registry.agent_registry import AgentRegistry
from runtime.registry.skill_registry import SkillRegistry

logger = logging.getLogger(__name__)


class UnitDispatcher:
    """
    Resuelve y ejecuta unidades (agent o skill).

    Responsabilidades:
    - Resolver agente o skill desde su registry.
    - Ejecutar process() o execute().
    - Normalizar resultado a ExecutionResult.
    - Capturar errores de ejecución.

    No:
    - Decide qué unidad ejecutar (lo decide el Engine).
    - Gestiona lifecycle del plan.
    - Construye contexto.
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        skill_registry: SkillRegistry,
    ) -> None:
        self.agent_registry = agent_registry
        self.skill_registry = skill_registry

    def dispatch(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:
        unit_type = step.unit_type
        unit_name = step.unit_name

        if unit_type == "agent":
            return self._execute_agent(plan, step, context)
        elif unit_type == "skill":
            return self._execute_skill(plan, step, context)
        else:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=f"Tipo de unidad inválido: {unit_type}",
                executor="dispatcher",
            )

    def _execute_agent(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:
        agent = self.agent_registry.get(step.unit_name)
        if not agent:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=f"Agent no encontrado: {step.unit_name}",
                executor="dispatcher",
            )

        step.mark_running()
        try:
            result = agent.process(plan, step, context)
            step.mark_completed(result)
            return ExecutionResult.success(
                plan_id=plan.id,
                result=result,
                executor=f"agent:{step.unit_name}",
                metadata={"step_id": step.id},
            )
        except Exception as exc:
            step.mark_failed(str(exc))
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=str(exc),
                executor=f"agent:{step.unit_name}",
            )

    def _execute_skill(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any],
    ) -> ExecutionResult:
        skill = self.skill_registry.get(step.unit_name)
        if not skill:
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=f"Skill no encontrada: {step.unit_name}",
                executor="dispatcher",
            )

        step.mark_running()
        try:
            result = skill.execute(plan, step, context)
            step.mark_completed(result)
            return ExecutionResult.success(
                plan_id=plan.id,
                result=result,
                executor=f"skill:{step.unit_name}",
                metadata={"step_id": step.id},
            )
        except Exception as exc:
            step.mark_failed(str(exc))
            return ExecutionResult.fail(
                plan_id=plan.id,
                error=str(exc),
                executor=f"skill:{step.unit_name}",
            )
