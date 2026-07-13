import re
from dataclasses import dataclass


@dataclass(slots=True)
class IntentResult:
    skill_name: str | None
    skill_params: dict | None


class IntentAnalyzer:
    """
    Analiza una consulta y determina qué Skill debe ejecutarse.

    Actualmente utiliza reglas (Regex), pero fue diseñado para
    poder evolucionar a un clasificador por IA sin modificar
    el Router.
    """

    @staticmethod
    def analyze(query: str) -> IntentResult:
        if not query:
            return IntentResult(None, None)

        q = query.lower().strip()

        # Análisis explícito de código
        if re.search(r"\b(analiza|revisa)\b.*\b(código|codigo|función|clase)\b", q):
            return IntentResult(
                "analyze",
                {"code_snippet": query},
            )

        # Análisis del proyecto
        if re.search(r"\b(analiza|revisa|problemas|errores)\b", q) and re.search(r"\b(proyecto|repo|actual|actualmente)\b", q):
            return IntentResult(
                "analyze_project",
                {},
            )

        # Generación
        if re.search(r"\b(crea|genera)\b", q) and re.search(r"\b(función|clase|proyecto)\b", q):
            return IntentResult(
                "code",
                {"task": query},
            )

        # README
        if re.search(r"\b(crea|genera)\b.*\b(readme)\b", q):
            return IntentResult(
                "readme",
                {"request": query},
            )

        return IntentResult(None, None)