from __future__ import annotations
from typing import Any
from agents.base import Agent
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from llm.router import LLMRouter


class MultiTurnAgent(Agent):
    name = "multi_turn"
    role = "Agente conversacional con memoria"

    def process(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> str:
        context = context or {}
        history = context.get("memory", "")
        enriched_context = {**context, "conversation_history": history}
        return LLMRouter().generate(plan=plan, context=enriched_context)
