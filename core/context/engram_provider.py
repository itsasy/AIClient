from core.engram_memory import EngramMemory
from core.context.provider import ContextProvider


class EngramProvider(ContextProvider):

    def __init__(self):

        self.engram = EngramMemory()

    def load(
        self,
        plan,
        context,
    ):

        if not plan.needs_engram:
            return

        context["engram"] = self.engram.get_context(
            plan.task,
            limit=plan.engram_limit,
        )
