from skills.base import Skill

class GenerateReadmeSkill(Skill):
    name = "generate_readme"
    description = "Genera README.md profesional"
    
    def execute(self, project_name: str = "", description: str = "", **kwargs):
        return {
            "type": "readme",
            "payload": {
                "project_name": project_name,
                "description": description,
            },
        }
