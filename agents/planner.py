from agents.base import Agent
from llm.router import LLMRouter
from skills.manager import SkillManager


class PlannerAgent(Agent):
    name = "planner"
    role = "Planificador y Ejecutor Autónomo"

    def process(self, task: str, context: dict = None) -> str:
        prompt = f"""Planifica y ejecuta esta tarea:

Tarea: {task}

Crea un plan detallado y luego indica qué skills o herramientas usarás para ejecutarlo."""
        return LLMRouter.generate(prompt)
