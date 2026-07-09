import logging

from core.project_inspector import ProjectInspector
from obsidian.search import ObsidianSearch

logger = logging.getLogger(__name__)


class ContextBuilder:
    def __init__(self):
        self.obsidian = ObsidianSearch()
        self.inspector = ProjectInspector()

    def build(self, query):
        project = self.inspector.inspect()
        obsidian = self.obsidian.build_context(query)

        return {
            "project": project,
            "obsidian": obsidian,
            "query": query,
        }

    def build_project_snapshot(self):
        return self.inspector.inspect()