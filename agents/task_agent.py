from agents.base import Agent
from llm.router import LLMRouter


class TaskAgent(Agent):
    name = "task"
    role = "Asistente general"
    skills = ("readme",)

    def process(
        self,
        task: str,
        context: dict | None = None,
    ) -> str:
        skill_name, skill_params = LLMRouter.detect_skill(task)

        if not self.supports_skill(skill_name):
            skill_name = None
            skill_params = None

        return LLMRouter.generate(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_params=skill_params,
        )