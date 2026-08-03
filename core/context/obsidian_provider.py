from obsidian.rag import RAG

from core.context.base import BaseContextProvider


class ObsidianProvider(BaseContextProvider):

    key = "obsidian"

    def __init__(self):

        self.rag = RAG()

    def load(
        self,
        plan,
        context,
    ) -> None:

        context[self.key] = self.rag.get_relevant_context(
            plan.original_task,
        )
