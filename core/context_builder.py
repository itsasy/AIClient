import logging

from core.project_inspector import ProjectInspector
from obsidian.search import ObsidianSearch

logger = logging.getLogger(__name__)


class ContextPayload(dict):
    def __contains__(self, item):
        if dict.__contains__(self, item):
            return True
        for value in self.values():
            if isinstance(value, str) and item in value:
                return True
        return False

    def __str__(self):
        return self._as_text(self)

    @staticmethod
    def _as_text(context):
        sections = []
        if context.get("project"):
            sections.append(f"=== PROYECTO ===\n{context['project']}")
        if context.get("obsidian"):
            sections.append(f"=== OBSIDIAN ===\n{context['obsidian']}")
        if context.get("query"):
            sections.append(f"=== CONSULTA ===\n{context['query']}")
        if context.get("memory"):
            sections.append(f"=== MEMORIA ===\n{context['memory']}")
        return "\n\n".join(sections)


class ContextBuilder:
    def __init__(self):
        self.obsidian = ObsidianSearch()
        self.inspector = ProjectInspector()

    def build(self, query):
        project = self.inspector.inspect()
        obsidian = self.obsidian.build_context(query)

        return ContextPayload({
            "project": project,
            "obsidian": obsidian,
            "query": query,
        })

    def build_project_snapshot(self):
        return self.inspector.inspect()

    def build_project_snapshot(self):
        return self.inspector.inspect()