from skills.base import Skill
from llm.router import LLMRouter


class CodeRefactorSkill(Skill):
    name = "refactor_code"
    description = "Refactoriza código a estándares modernos"

    def execute(self, code: str, standards: str = "", **kwargs):
        prompt = f"""Refactoriza este código según estándares modernos:

Código original:
{code}

Estándares deseados:
{standards or "Clean Code, SOLID, tipado, manejo de errores, Laravel 11"}

Proporciona:
1. Código refactorizado
2. Cambios realizados
3. Mejoras aplicadas"""
        return LLMRouter.generate(prompt)
