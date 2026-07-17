from obsidian.search import ObsidianSearch


class RAG:
    def __init__(self):
        self.search = ObsidianSearch()

    def get_relevant_context(self, query: str, max_results: int = 8) -> str:
        results = self.search.search(query, max_results=max_results)

        if not results:
            return "No se encontró información relevante en Obsidian.\n"

        context = "=== CONOCIMIENTO RELEVANTE (RAG) ===\n\n"
        for r in results:
            context += f"📄 {r['path']}\n{r['content'][:900]}\n{'─' * 80}\n\n"

        return context
