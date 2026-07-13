from agents.base import Agent
from llm.router import LLMRouter

class MultiTurnAgent(Agent):
    name = "multi_turn"
    role = "Agente conversacional persistente"
    
    def process(self, task: str, context: dict = None) -> str:
        history = context.get("memory", "") if context else ""
        prompt = f"""Historial anterior:\n{history}\n\nNueva tarea: {task}\nResponde coherentemente manteniendo el contexto."""
        return LLMRouter.generate(prompt)