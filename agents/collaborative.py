from agents.manager import AgentManager


class CollaborativeSystem:
    def __init__(self):
        self.manager = AgentManager()

    def collaborate(self, task: str, context: dict = None):
        architect_response = self.manager.delegate(task + " [ARQUITECTURA]", context)
        coder_response = self.manager.delegate(task + " [IMPLEMENTACIÓN]", context)

        return f"""**Equipo Colaborativo:**

**Arquitecto:**
{architect_response}

**Programador:**
{coder_response}

**Recomendación final:** Integra ambas perspectivas para un resultado completo."""
