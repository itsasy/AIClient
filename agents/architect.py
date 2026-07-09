from agents.base import Agent
from llm.router import LLMRouter

class ArchitectAgent(Agent):
    name = "Architect"
    role = "Define arquitectura y estándares"
    skills = ["analyze_project"]
    
    def process(self, task: str) -> str:
        prompt = f"""Eres un Arquitecto de Software Senior.
Tarea: {task}

Proporciona:
1. Arquitectura recomendada
2. Estructura de carpetas
3. Patrones a usar
4. Decisiones técnicas clave"""
        return LLMRouter.generate(prompt)
