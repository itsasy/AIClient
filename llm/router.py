import re

from skills.manager import SkillManager


class LLMRouter:
    skill_manager = SkillManager()

    @staticmethod
    def detect_skill(query: str):
        if not query:
            return None, None

        q = query.lower()

        if re.search(r"\b(crea|genera)\b", q) and re.search(r"\b(readme|read me)\b", q):
            return "readme", {"project_name": query}

        if re.search(r"\b(analiza|revisa)\b", q) and re.search(
            r"\b(proyecto|repo|arquitectura|estructura|estándares|diseño)\b",
            q,
        ):
            return "analyze_project", {"project_path": "."}

        if re.search(r"\b(analiza|revisa)\b", q) and re.search(
            r"\b(código|codigo|archivo|módulo|modulo)\b",
            q,
        ):
            return "analyze", {"code_snippet": query}

        if re.search(r"\b(crea|genera|implementa)\b", q) and re.search(
            r"\b(función|funcion|clase|script|codigo|código)\b",
            q,
        ):
            return "code", {"task": query}

        return None, None

    @staticmethod
    def _provider():
        from .gemini import GeminiProvider

        return GeminiProvider()

    @staticmethod
    def generate(task: str, context: str, skill_name=None, skill_params=None):
        provider = LLMRouter._provider()

        if skill_name:
            skill_result = LLMRouter.skill_manager.execute(skill_name, **(skill_params or {}))

            prompt = f"""
Eres un asistente experto.

Consulta del usuario:

{task}

=======================

Contexto:

{context}

=======================

Skill ejecutada:

{skill_name}

Resultado:

{skill_result}

=======================

Utiliza el resultado de la skill como base principal.
No inventes información.
"""
            return provider.generate(prompt)

        prompt = f"""
Eres un asistente experto.

Consulta:

{task}

=======================

Contexto:

{context}
"""

        return provider.generate(prompt)

