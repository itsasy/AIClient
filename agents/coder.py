from agents.base import Agent
from llm.router import LLMRouter


class CoderAgent(Agent):
    name = "coder"
    role = "Desarrollador de Software Senior"
    skills = ("code", "analyze")

    def process(
        self,
        task: str,
        context: dict | None = None,
    ) -> str:
        skill_name, skill_params = LLMRouter.detect_skill(task)

        return LLMRouter.generate(
            task=task,
            context=context or {},
            skill_name=skill_name,
            skill_params=skill_params,
        )