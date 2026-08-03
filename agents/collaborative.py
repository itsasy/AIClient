from __future__ import annotations

from typing import Any

from agents.manager import AgentManager

from core.execution_plan import ExecutionPlan


class CollaborativeSystem:
    """
    Sistema colaborativo entre agentes.

    Ejecuta un mismo ExecutionPlan desde
    perspectivas diferentes.

    No crea planes.
    No analiza intención.
    No resuelve contexto.
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

        architect_plan = self._clone_plan(
            plan,
        )

        architect_plan.agent = "architect"

        architect_response = self.manager.delegate(
            plan=architect_plan,
            context=context.copy(),
        )

        # ==================================================
        # Implementación
        # ==================================================

        coder_plan = self._clone_plan(
            plan,
        )

        coder_plan.agent = "coder"

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

    def _clone_plan(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionPlan:

        return ExecutionPlan(
            id=plan.id,
            created_at=plan.created_at,
            original_task=plan.original_task,
            objective=plan.objective,
            intent=plan.intent,
            intent_category=plan.intent_category,
            execution_mode=plan.execution_mode,
            skills=list(plan.skills),
            required_tools=list(plan.required_tools),
            context_requirements=list(plan.context_requirements),
            params=dict(plan.params),
            constraints=list(plan.constraints),
            metadata=dict(plan.metadata),
            preferred_provider=plan.preferred_provider,
            temperature=plan.temperature,
            max_tokens=plan.max_tokens,
            system_role=plan.system_role,
        )
