from skills.base import Skill

class GenerateReadmeSkill(Skill):
    name = "generate_readme"
    description = "Genera README.md profesional"
    
    def execute(self, project_name: str = "", description: str = "", **kwargs) -> str:
        prompt = f"""Crea un README.md profesional para el proyecto: {project_name}
Descripción: {description}
Incluye: descripción, instalación, uso, estructura y contribución."""
        return prompt
