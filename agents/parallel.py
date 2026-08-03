from __future__ import annotations

import asyncio
from typing import Any

from agents.manager import AgentManager

from core.execution_plan import ExecutionPlan


class ParallelAgentSystem:
    """
    Ejecuta múltiples agentes sobre un mismo ExecutionPlan.

    Responsabilidades:

    - Ejecutar agentes especializados en paralelo.
    - Compartir contexto.
    - Consolidar respuestas.

    No:

    - Analiza intención.
    - Crea ExecutionPlans.
    - Selecciona LLM providers.
    """

    def __init__(self):

        self.manager = AgentManager()

    async def run(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = context or {}

        architect_plan = self._clone_plan(
            plan,
        )

        architect_plan.agent = "architect"

        coder_plan = self._clone_plan(
            plan,
        )

        coder_plan.agent = "coder"

        architect_task = asyncio.to_thread(
            self.manager.delegate,
            architect_plan,
            context.copy(),
        )

        coder_task = asyncio.to_thread(
            self.manager.delegate,
            coder_plan,
            context.copy(),
        )

        architect, coder = await asyncio.gather(
            architect_task,
            coder_task,
        )

        return "**Arquitecto:**\n" f"{architect}\n\n" "**Programador:**\n" f"{coder}"

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
