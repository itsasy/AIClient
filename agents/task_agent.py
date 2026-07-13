from agents.base import Agent
from llm.router import LLMRouter


class TaskAgent(Agent):
    name = "task"
    role = "Asistente general"
    skills = ()

    def process(
        self,
        task: str,
        context: dict | None = None,
    ) -> str:
        return LLMRouter.generate(
            task=task,
            context=context or {},
        )