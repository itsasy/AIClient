from agents.base import Agent
from llm.router import LLMRouter
from core.execution_plan import ExecutionPlan


class MultiTurnAgent(Agent):

    name = "multi_turn"

    role = "Agente conversacional"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        history = ""

        if context:
            history = context.get("memory", "")

        prompt = f"""
Historial

{history}

Nueva tarea

{plan.task}

Mantén coherencia.
"""

        cloned = ExecutionPlan(
            task=prompt,
            skill_name=plan.skill_name,
            skill_params=plan.skill_params,
            needs_project=plan.needs_project,
            needs_obsidian=plan.needs_obsidian,
            needs_memory=plan.needs_memory,
            needs_engram=plan.needs_engram,
            needs_spec=plan.needs_spec,
            requires_llm=plan.requires_llm,
            requires_execution=plan.requires_execution,
            requires_self_critic=plan.requires_self_critic,
            metadata=plan.metadata.copy(),
        )

        return LLMRouter.generate(
            plan=cloned,
            context=context or {},
        )
