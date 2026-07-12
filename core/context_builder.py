from core.project_inspector import ProjectInspector
from obsidian.search import ObsidianSearch


class ContextBuilder:
    def __init__(self):
        self.obsidian = ObsidianSearch()
        self.inspector = ProjectInspector()

    def build(self, query: str) -> dict:
        return {
            "project": self.inspector.inspect(),
            "obsidian": self.obsidian.build_context(query),
            "query": query,
        }

    def build_project_snapshot(self) -> str:
        return self.inspector.inspect()