from __future__ import annotations

from typing import Any

from agents.manager import AgentManager

from core.execution_plan import ExecutionPlan


class CollaborativeSystem:
    """
    Sistema colaborativo entre agentes.
    """

    def __init__(self):

        self.manager = AgentManager()

    def collaborate(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = context or {}

        # ==================================================
        # Arquitectura
        # ==================================================

        architect_plan = self._clone_plan(plan)
        architect_plan.execution_unit_type = "agent"
        architect_plan.execution_unit = "architect"

        architect_response = self.manager.delegate(
            plan=architect_plan,
            context=context.copy(),
        )

        # ==================================================
        # Implementación
        # ==================================================

        coder_plan = self._clone_plan(plan)
        coder_plan.execution_unit_type = "agent"
        coder_plan.execution_unit = "coder"

        coder_response = self.manager.delegate(
            plan=coder_plan,
            context=context.copy(),
        )

        return (
            "**Equipo Colaborativo:**\n\n"
            "**Arquitecto:**\n"
            f"{architect_response}\n\n"
            "**Programador:**\n"
            f"{coder_response}\n\n"
            "**Recomendación final:** "
            "Integrar ambas perspectivas."
        )

    # ==================================================
    # Helpers
    # ==================================================

    def _clone_plan(self, plan: ExecutionPlan) -> ExecutionPlan:

        return ExecutionPlan(
            id=plan.id,
            created_at=plan.created_at,
            original_task=plan.original_task,
            objective=plan.objective,
            intent=plan.intent,
            intent_category=plan.intent_category,
            execution_mode=plan.execution_mode,
            execution_unit_type=plan.execution_unit_type,
            execution_unit=plan.execution_unit,
            steps=list(plan.steps),
            context_requirements=list(plan.context_requirements),
            params=dict(plan.params),
            constraints=list(plan.constraints),
            metadata=dict(plan.metadata),
            max_retries=plan.max_retries,
            stop_on_error=plan.stop_on_error,
        )
