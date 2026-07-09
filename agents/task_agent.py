from agents.base import Agent
from llm.router import LLMRouter
from skills.manager import SkillManager

class TaskAgent(Agent):
    name = "TaskExecutor"
    role = "Ejecuta tareas prácticas"
    
    def process(self, task: str) -> str:
        prompt = f"""Eres un agente autónomo. Tarea: {task}
Decide si necesitas usar skills o LLM.
Sé concreto y accionable."""
        return LLMRouter.generate(prompt)
