from typing import Any
from core.memory import ConversationMemory
from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan


class MemoryProvider(BaseContextProvider):

    key = "memory"

    def __init__(self):

        self.memory = ConversationMemory()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        memory = self.memory.get_context()

        if not memory:
            return

        context[self.key] = memory
