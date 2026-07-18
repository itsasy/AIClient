from agents.base import Agent
from llm.router import LLMRouter


class PlannerAgent(Agent):
    name = "planner"
    role = "Planificador Autónomo"

    def process(self, task: str, context: dict = None) -> str:
        prompt = f"""Planifica esta tarea de forma autónoma y detallada:

Tarea: {task}

Crea un plan paso a paso, identifica skills necesarias y posibles riesgos."""
        return LLMRouter.generate(prompt)
