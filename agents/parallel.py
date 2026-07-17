from agents.manager import AgentManager


class ParallelAgentSystem:
    def __init__(self):
        self.manager = AgentManager()

    def run(self, task: str, context: dict = None):
        architect = self.manager.delegate(task + " [ARQUITECTURA]", context)
        coder = self.manager.delegate(task + " [CÓDIGO]", context)

        return f"""**Arquitecto:**\n{architect}\n\n**Programador:**\n{coder}"""
