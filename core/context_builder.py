import logging

from obsidian.search import ObsidianSearch
from core.project_inspector import ProjectInspector

logger = logging.getLogger(__name__)

class ContextBuilder:

    def __init__(self):

        self.obsidian = ObsidianSearch()
        self.inspector = ProjectInspector()

    def build(self, query):

        project = self.inspector.inspect()

        obsidian = self.obsidian.build_context(query)

        return f"""
=== PROYECTO ===

{project}

=== OBSIDIAN ===

{obsidian}

=== CONSULTA ===

{query}
"""