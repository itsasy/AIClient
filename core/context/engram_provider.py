from core.engram_memory import EngramMemory
from core.context.base import BaseContextProvider


class EngramProvider(BaseContextProvider):

    key = "engram"

    def __init__(self):

        self.engram = EngramMemory()

    def load(
        self,
        plan,
        context,
    ) -> None:

        context[self.key] = {
            "memory": self.engram.get_context(
                plan.original_task,
                limit=5,
            ),
            "skills": self.engram.find_skills(
                plan.original_task,
            ),
        }
