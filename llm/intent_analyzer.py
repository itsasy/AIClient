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

        #
        # README
        #

        if re.search(
            r"\b(crea|crear|genera|generar|haz)\b.*"
            r"\b(readme|documentación|documentacion)\b",
            q,
        ):
            return IntentResult(
                "readme",
                {
                    "request": query,
                },
            )

        #
        # Análisis de código
        #

        if re.search(
            r"\b(analiza|analizar|revisa|revisar)\b.*"
            r"\b("
            r"código|codigo|función|funcion|"
            r"clase|archivo|módulo|modulo"
            r")\b",
            q,
        ):
            explicit_code_markers = (
                "def ",
                "class ",
                "import ",
                "return ",
                "```",
            )

            if any(
                marker in q
                for marker in explicit_code_markers
            ):
                return IntentResult(
                    "analyze",
                    {
                        "code_snippet": query,
                    },
                )

        #
        # Proyecto actual
        #

        project_intent = re.search(
            r"\b("
            r"analiza|analizar|revisa|revisar|"
            r"evalúa|evaluar|inspecciona|inspeccionar|"
            r"problemas|errores|deuda"
            r")\b",
            q,
        )

        project_reference = re.search(
            r"\b("
            r"proyecto|repo|repositorio|"
            r"arquitectura|estructura|"
            r"código actual|codigo actual|"
            r"mi código|mi codigo|"
            r"actualmente|sistema actual"
            r")\b",
            q,
        )

        if project_intent and project_reference:
            return IntentResult(
                "analyze_project",
                {},
            )

        #
        # Generación de código
        #

        if re.search(
            r"\b("
            r"crea|crear|genera|generar|"
            r"implementa|implementar|escribe"
            r")\b.*"
            r"\b("
            r"función|funcion|clase|script|"
            r"endpoint|código|codigo|proyecto"
            r")\b",
            q,
        ):
            return IntentResult(
                "code",
                {
                    "task": query,
                },
            )

        return IntentResult(
            None,
            None,
        )