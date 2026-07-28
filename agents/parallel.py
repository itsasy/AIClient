from agents.manager import AgentManager


class ParallelAgentSystem:
    def __init__(self):
        self.manager = AgentManager()

    def run(
        self,
        task: str,
        context: dict[str, object] | None = None,
    ) -> str:
        shared_context = context if context is not None else {}

        architect = self.manager.delegate(
            f"{task} [ARQUITECTURA]",
            shared_context.copy(),
        )

        coder = self.manager.delegate(
            f"{task} [CÓDIGO]",
            shared_context.copy(),
        )

        return f"""**Arquitecto:**
{architect}

**Programador:**
{coder}"""
