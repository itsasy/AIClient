from agents.base import Agent
from llm.router import LLMRouter
from skills.manager import SkillManager

class CoderAgent(Agent):
    name = "Coder"
    role = "Desarrollador Senior"
    skills = ["code", "analyze", "shell"]
    
    def process(self, task: str) -> str:
        # Intentar skill primero
        if "genera" in task.lower() or "crea código" in task.lower():
            return LLMRouter.generate(task)
        else:
            return LLMRouter.generate(f"[ROL: Programador Experto] {task}")
