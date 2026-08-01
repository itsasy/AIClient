from context.project_provider import ProjectProvider
from context.obsidian_provider import ObsidianProvider
from context.engram_provider import EngramProvider
from context.memory_provider import MemoryProvider
from context.spec_provider import SpecProvider
from context.documents_provider import DocumentsProvider


class ContextManager:

    def __init__(self):

        self.providers = [
            ProjectProvider(),
            ObsidianProvider(),
            EngramProvider(),
            MemoryProvider(),
            SpecProvider(),
            DocumentsProvider(),
        ]

    def build(self, plan):

        context = {
            "query": plan.task,
        }

        for provider in self.providers:

            provider.load(
                plan,
                context,
            )

        return context
