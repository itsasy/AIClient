from core.memory import ConversationMemory
from core.context.base import BaseContextProvider


class MemoryProvider(BaseContextProvider):

    key = "memory"

    def __init__(self):

        self.memory = ConversationMemory()

    def load(
        self,
        plan,
        context,
    ) -> None:

        context[self.key] = self.memory.get_context()
