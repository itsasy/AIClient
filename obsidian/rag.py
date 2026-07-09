from obsidian.search import ObsidianSearch
import re

class SimpleRAG:
    def __init__(self):
        self.search = ObsidianSearch()
    
    def get_relevant_context(self, query: str, max_tokens: int = 2000) -> str:
        results = self.search.search(query, max_results=4)
        
        context = "=== CONOCIMIENTO RELEVANTE DE TU SEGUNDO CEREBRO ===\n\n"
        total = 0
        for r in results:
            snippet = r['content'][:600]
            context += f"📄 {r['path']}\n{snippet}\n\n"
            total += len(snippet)
            if total > max_tokens:
                break
        return context
