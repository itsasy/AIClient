from agents.base import Agent
from llm.router import LLMRouter
from core.execution_plan import ExecutionPlan


class ArchitectAgent(Agent):
    name = "architect"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        return LLMRouter.generate(
            plan=plan,
            context=context or {},
        )
