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

import re
from dataclasses import dataclass


@dataclass(slots=True)
class IntentResult:
    skill_name: str | None
    skill_params: dict | None


class IntentAnalyzer:
    """
    Analiza una consulta y determina qué Skill debe ejecutarse.
    """

    @staticmethod
    def analyze(query: str) -> IntentResult:
        if not query:
            return IntentResult(None, None)

        q = query.lower().strip()

        # ------------------------------------------------------------
        # 1. DETECCIÓN DE PROYECTOS (Laravel, React, Vue, Django, etc.)
        # ------------------------------------------------------------
        if re.search(r"\b(laravel|react|vue|django|fullstack)\b", q) and re.search(
            r"\b(proyecto|crea|genera|nuevo)\b", q
        ):
            return IntentResult(
                "laravel_project",
                {"name": query}  # Pasamos la consulta completa, luego la skill extraerá el nombre
            )

        # ------------------------------------------------------------
        # 2. DETECCIÓN DE SHELL / COMANDOS
        # ------------------------------------------------------------
        if re.search(r"\b(ejecuta|corre|run)\b", q) and re.search(
            r"\b(comando|ls|git|docker|composer|php|artisan|npm|cd|pwd|tree|cat|grep)\b", q
        ):
            return IntentResult(
                "shell",
                {"command": query}  # La skill extraerá el comando real
            )

        # ------------------------------------------------------------
        # 3. DETECCIÓN DE DOCKER (comandos específicos)
        # ------------------------------------------------------------
        if re.search(r"\bdocker\b", q) and re.search(
            r"\b(ps|images|logs|status|inspect|start|stop|restart)\b", q
        ):
            # Como 'docker' también puede caer en shell, lo ponemos aquí con prioridad
            return IntentResult(
                "docker",
                {"action": q}
            )

        # ------------------------------------------------------------
        # 4. REGLAS EXISTENTES (sin modificar su lógica original)
        # ------------------------------------------------------------

        # Análisis explícito de código
        if re.search(r"\b(analiza|revisa)\b.*\b(código|codigo|función|clase)\b", q):
            return IntentResult(
                "analyze",
                {"code_snippet": query},
            )

        # Análisis del proyecto
        if re.search(r"\b(analiza|revisa|problemas|errores)\b", q) and re.search(
            r"\b(proyecto|repo|actual|actualmente)\b", q
        ):
            return IntentResult(
                "analyze_project",
                {},
            )

        # Generación de código genérica (si no es Laravel, cae aquí)
        if re.search(r"\b(crea|genera)\b", q) and re.search(
            r"\b(función|clase|script|endpoint)\b", q
        ):
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