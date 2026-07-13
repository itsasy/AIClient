from agents.base import Agent
from llm.router import LLMRouter


class ArchitectAgent(Agent):
    name = "architect"
    role = "Arquitecto de Software Senior"
    skills = ("analyze_project",)

    def process(
        self,
        task: str,
        context: dict | None = None,
    ) -> str:
        return LLMRouter.generate(
            task=task,
            context=context or {},
            skill_name="analyze_project",
            skill_params={},
        )