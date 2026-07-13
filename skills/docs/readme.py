from core.project_inspector import ProjectInspector
from skills.base import Skill


class GenerateReadmeSkill(Skill):
    name = "readme"
    description = "Genera un README profesional basado en el proyecto real"

    def __init__(self):
        self.inspector = ProjectInspector()

    def execute(
        self,
        request: str = "",
        description: str = "",
        **kwargs,
    ):
        snapshot = self.inspector.inspect()

        return {
            "type": "readme",
            "payload": {
                "request": request,
                "description": description,
                "snapshot": snapshot,
            },
        }