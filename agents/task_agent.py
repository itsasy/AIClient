from agents.base import Agent
from llm.router import LLMRouter


class TaskAgent(Agent):
    name = "task"

    def process(
        self,
        task: str,
        context: dict | None = None,
        skill_name: str | None = None,
        skill_params: dict | None = None,
    ) -> str:
        return LLMRouter.generate(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_params=skill_params,
        )