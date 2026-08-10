from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan
from core.memory import ConversationMemory


class MemoryProvider(BaseContextProvider):

    key = "memory"

    def __init__(self) -> None:
        self.memory = ConversationMemory()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        memory = self.memory.get_context()

        if not memory:
            return {}

        return {
            "history": memory,
        }
