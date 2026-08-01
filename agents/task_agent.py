from agents.base import Agent
from core.execution_plan import ExecutionPlan
from llm.router import LLMRouter


class TaskAgent(Agent):

    name = "task"

    role = "Agente general de resolución"

    def process(
        self,
        plan: ExecutionPlan,
        context: dict | None = None,
    ) -> str:

        return LLMRouter.generate(
            plan=plan,
            context=context or {},
        )
