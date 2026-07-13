from obsidian.search import ObsidianSearch

class SimpleRAG:
    def __init__(self):
        self.search = ObsidianSearch()
    
    def get_relevant_context(self, query: str, max_results: int = 5) -> str:
        results = self.search.search(query, max_results=max_results)
        
        if not results:
            return ""
        
        context = "=== CONOCIMIENTO RELEVANTE ===\n\n"
        for r in results:
            context += f"📄 {r['path']}\n{r['content'][:700]}\n\n"
        
        return context