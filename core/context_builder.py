from obsidian.search import ObsidianSearch

class ContextBuilder:
    def __init__(self):
        self.obsidian = ObsidianSearch()
    
    def build(self, query: str) -> str:
        context = self.obsidian.build_context(query)
        context += f"\n=== CONSULTA ACTUAL ===\n{query}\n"
        return context
