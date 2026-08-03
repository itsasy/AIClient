from core.project_inspector import ProjectInspector
from core.context.base import BaseContextProvider


class ProjectProvider(BaseContextProvider):

    key = "project"

    def __init__(self):

        self.inspector = ProjectInspector()

    def load(
        self,
        plan,
        context,
    ) -> None:

        context[self.key] = self.inspector.inspect()
