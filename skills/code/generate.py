from skills.base import Skill

class GenerateCodeSkill(Skill):
    name = "generate_code"
    description = "Genera código en Python, PHP, etc."
    
    def execute(self, language: str = "python", task: str = "", **kwargs) -> str:
        prompt = f"""Escribe código {language} limpio y moderno para: {task}
Incluye comentarios, manejo de errores y buenas prácticas."""
        return prompt
