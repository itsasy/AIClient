from agents.base import Agent
from llm.router import LLMRouter


class MultiTurnAgent(Agent):
    name = "multi_turn"
    role = "Agente conversacional con memoria"

    def process(self, task: str, context: dict = None) -> str:
        history = context.get("memory", "") if context else ""
        prompt = f"""Historial:\n{history}\n\nNueva tarea: {task}\nMantén coherencia y contexto."""
        return LLMRouter.generate(prompt)
