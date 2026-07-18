from obsidian.search import ObsidianSearch


class RAG:
    def __init__(self):
        self.search = ObsidianSearch()

    def get_relevant_context(self, query: str, max_results: int = 8) -> str:
        results = self.search.search(query, max_results=max_results)

        if not results:
            return "No se encontró información relevante en Obsidian.\n"

        context_lines = [
            "=== CONOCIMIENTO RELEVANTE (RAG HÍBRIDO) ===",
            f"Búsqueda combinada: FTS5 + semántica (modelo all-MiniLM-L6-v2)",
            ""
        ]

        for r in results:
            snippet = r.get("snippet", "")
            content = r.get("content", "")
            score = r.get("final_score", r.get("score", 0))

            display_content = snippet if snippet else content[:800]

            context_lines.append(f"📄 {r['path']} (relevancia: {score:.3f})")
            context_lines.append(display_content)
            context_lines.append("─" * 80)
            context_lines.append("")

        return "\n".join(context_lines)