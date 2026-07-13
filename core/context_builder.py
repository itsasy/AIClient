from core.project_inspector import ProjectInspector
from obsidian.rag import SimpleRAG

class ContextBuilder:
    def __init__(self):
        self.rag = SimpleRAG()
        self.inspector = ProjectInspector()

    def build(self, query: str) -> dict:
        project = self.inspector.inspect()[:4000]
        return {
            "project": project, #self.inspector.inspect()
            "obsidian": self.rag.get_relevant_context(query),
            "query": query,
        }