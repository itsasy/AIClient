from core.project_inspector import ProjectInspector
from core.context.provider import ContextProvider


class ProjectProvider(ContextProvider):

    def __init__(self):
        self.inspector = ProjectInspector()

    def load(
        self,
        plan,
        context,
    ):

        if not plan.needs_project:
            return

        context["project"] = self.inspector.inspect()
