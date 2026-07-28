from agents.manager import AgentManager


class CollaborativeSystem:
    def __init__(self):
        self.manager = AgentManager()

    def collaborate(
        self,
        task: str,
        context: dict[str, object] | None = None,
    ) -> str:
        shared_context = context if context is not None else {}

        architect_response = self.manager.delegate(
            f"{task} [ARQUITECTURA]",
            shared_context.copy(),
        )

        coder_response = self.manager.delegate(
            f"{task} [IMPLEMENTACIÓN]",
            shared_context.copy(),
        )

        return f"""**Equipo Colaborativo:**

**Arquitecto:**
{architect_response}

**Programador:**
{coder_response}

**Recomendación final:** Integra ambas perspectivas para un resultado completo."""
