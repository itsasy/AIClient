from core.memory import ConversationMemory
from core.context.provider import ContextProvider


class MemoryProvider(ContextProvider):

    def __init__(self):

        self.memory = ConversationMemory()

    def load(
        self,
        plan,
        context,
    ):

        if not plan.needs_memory:
            return

        context["memory"] = self.memory.get_context()
