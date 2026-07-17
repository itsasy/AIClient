from agents.base import Agent
from llm.router import LLMRouter
from skills.manager import SkillManager


class ExecutorAgent(Agent):
    name = "executor"
    role = "Ejecutor Autónomo de Tareas"

    def process(self, task: str, context: dict = None) -> str:
        prompt = f"""Ejecuta esta tarea de forma autónoma:

Tarea: {task}

Usa las skills y herramientas disponibles para completarla paso a paso."""
        return LLMRouter.generate(prompt)
