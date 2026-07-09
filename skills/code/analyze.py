from skills.base import Skill

class AnalyzeCodeSkill(Skill):
    name = "analyze_code"
    description = "Analiza código existente"
    
    def execute(self, code_snippet: str = "", language: str = "python", **kwargs) -> str:
        prompt = f"""Analiza este código {language} y dame:
1. Problemas / Mejoras
2. Seguridad
3. Buenas prácticas
4. Sugerencias de refactor

Código:
{code_snippet}"""
        return prompt
