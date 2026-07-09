from skills.base import Skill


class ProjectAnalyzerSkill(Skill):

    name = "analyze_project"

    description = "Analiza un proyecto completo"

    def execute(self, project_snapshot="", **kwargs):

        return {
            "analysis": "project",
            "snapshot": project_snapshot
        }