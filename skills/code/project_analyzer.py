from core.project_inspector import ProjectInspector
from skills.base import Skill


class ProjectAnalyzerSkill(Skill):

    name = "analyze_project"

    description = "Analiza un proyecto completo"

    def __init__(self):
        self.inspector = ProjectInspector()

    def execute(self, **kwargs):
        snapshot = self.inspector.inspect()

        return {
            "type": "project_analysis",
            "payload": snapshot,
        }