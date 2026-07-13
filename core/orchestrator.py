from agents.manager import AgentManager
from core.context_builder import ContextBuilder
from core.memory import ConversationMemory


class Orchestrator:
    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()
        self.agent_manager = AgentManager()

    def process(self, task: str) -> str:
        context_payload = self.context_builder.build(task)

        memory_context = self.memory.get_context()

        if memory_context:
            context_payload["memory"] = memory_context

        response = self.agent_manager.delegate(
            task=task,
            context=context_payload,
        )

        self.memory.add(task, response)

        return response