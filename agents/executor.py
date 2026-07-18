from agents.base import Agent
from llm.router import LLMRouter
from skills.manager import SkillManager


class ExecutorAgent(Agent):
    name = "executor"
    role = "Ejecutor Autónomo de Tareas"

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