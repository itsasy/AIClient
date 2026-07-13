from core.project_inspector import ProjectInspector
from obsidian.search import ObsidianSearch


class ContextBuilder:
    PROJECT_KEYWORDS = (
        "proyecto",
        "repo",
        "repositorio",
        "arquitectura",
        "estructura",
        "código actual",
        "codigo actual",
        "readme",
        "deuda técnica",
        "deuda tecnica",
        "analiza este proyecto",
        "analiza mi proyecto",
    )

    def __init__(self):
        self.obsidian = ObsidianSearch()
        self.inspector = ProjectInspector()

    def build(self, query: str) -> dict:
        context = {
            "query": query,
        }

        if self._requires_project_context(query):
            context["project"] = (self.inspector.inspect_snapshot())

        obsidian_context = self.obsidian.build_context(query)

        if obsidian_context:
            context["obsidian"] = obsidian_context

        return context

    def build_project_snapshot(self) -> str:
        return self.inspector.inspect_snapshot()

    def _requires_project_context(
        self,
        query: str,
    ) -> bool:
        q = (query or "").lower()

        return any(
            keyword in q
            for keyword in self.PROJECT_KEYWORDS
        )