from agents.architect import ArchitectAgent
from agents.coder import CoderAgent

class AgentManager:
    def __init__(self):
        self.agents = {
            "architect": ArchitectAgent(),
            "coder": CoderAgent(),
        }
    
    def get_agent(self, task: str):
        if "arquitectura" in task.lower() or "estándares" in task.lower() or "diseño" in task.lower():
            return self.agents["architect"]
        return self.agents["coder"]
    
    def delegate(self, task: str):
        agent = self.get_agent(task)
        return agent.process(task)
