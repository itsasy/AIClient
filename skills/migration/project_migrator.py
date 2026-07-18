from skills.base import Skill
from core.project_inspector import ProjectInspector


class ProjectMigratorSkill(Skill):
    name = "migrate_project"
    description = "Migra proyecto antiguo a estándares modernos"

    def __init__(self):
        self.inspector = ProjectInspector()

    def execute(self, old_project_path: str = ".", new_standards: str = "", **kwargs):
        snapshot = self.inspector.inspect()

        return {
            "type": "migration",
            "payload": {
                "snapshot": snapshot,
                "new_standards": new_standards
                or "Laravel 11, Docker, Sanctum, buenas prácticas modernas, arquitectura limpia",
                "old_project_path": old_project_path,
            },
        }
