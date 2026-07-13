from agents.manager import AgentManager
from core.context_builder import ContextBuilder
from core.memory import ConversationMemory


class Orchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()
        self.agent_manager = AgentManager()

    def process(self, task: str) -> str:
        context = self.context_builder.build(task)

        memory = self.memory.get_context()

        if memory:
            context["memory"] = memory

        response = self.agent_manager.delegate(
            task=task,
            context=context,
        )

        self.memory.add(task, response)

        return response