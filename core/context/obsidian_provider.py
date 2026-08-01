from obsidian.rag import RAG
from core.context.provider import ContextProvider


class ObsidianProvider(ContextProvider):

    def __init__(self):

        self.rag = RAG()

    def load(
        self,
        plan,
        context,
    ):

        if not plan.needs_obsidian:
            return

        context["obsidian"] = self.rag.get_relevant_context(plan.task)
