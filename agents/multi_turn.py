from agents.base import Agent
from core.execution_plan import ExecutionPlan
from llm.router import LLMRouter


class MultiTurnAgent(Agent):

    name = "multi_turn"

    role = "Agente conversacional con memoria"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        history = ""

        if context:
            history = context.get(
                "memory",
                "",
            )

        enriched_context = {
            **(context or {}),
            "conversation_history": history,
        }

        return LLMRouter.generate(
            plan=plan,
            context=enriched_context,
        )
