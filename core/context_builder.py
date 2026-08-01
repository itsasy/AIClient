class ContextBuilder:

    def __init__(self):
        self._rag = None

    @property
    def rag(self):
        if self._rag is None:
            from obsidian.rag import RAG

            self._rag = RAG()

        return self._rag

    def build(self, plan) -> dict:

        context = {
            "query": plan.task,
        }

        if plan.needs_project:

            context["project"] = self.inspector.inspect()

        if plan.needs_obsidian:

            context["obsidian"] = self.rag.get_relevant_context(plan.task)

        return context

    def get_ingested_docs(self):

        return self.ingestor.list_ingested()
