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

        # 1. DETECCIÓN DE LARAVEL / PROYECTOS COMPLETOS
        if re.search(
            r"\b(laravel|react|vue|django|fullstack)\b.*\b(proyecto|crea|genera|nuevo)\b",
            q,
        ):
            return IntentResult(
                "laravel_project",
                {
                    "name": query
                },  # Pasamos la consulta completa para extraer el nombre después
            )

        # 2. DETECCIÓN DE SHELL / COMANDOS
        if re.search(r"\b(ejecuta|corre|run)\b", q) and re.search(
            r"\b(comando|ls|git|docker|composer|php|artisan|npm|cd)\b", q
        ):
            return IntentResult(
                "shell", {"command": query}  # El ShellTool recibe el comando completo
            )

        # 3. DETECCIÓN DE DOCKER
        if re.search(r"\b(docker)\b", q) and re.search(
            r"\b(ps|images|logs|status|inspect)\b", q
        ):
            return IntentResult("docker", {"action": q})  # DockerTool espera 'action'

        # --- REGLAS EXISTENTES ---

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

        # Generación de código genérica
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
