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
            name_match = re.search(
                r"llamado\s+(\S+)|nombre\s+(\S+)|proyecto\s+(\S+)$", q
            )
            if name_match:
                name = (
                    name_match.group(1)
                    or name_match.group(2)
                    or name_match.group(3)
                    or "mi_proyecto"
                )
            else:
                name = q.split()[-1] if q.split() else "mi_proyecto"
            return IntentResult("laravel_project", {"name": name})

        # ------------------------------------------------------------
        # 2. DETECCIÓN DE SHELL / COMANDOS (extrae el comando real)
        # ------------------------------------------------------------
        if re.search(r"\b(ejecuta|corre|run)\b", q) and re.search(
            r"\b(comando|ls|git|docker|composer|php|artisan|npm|cd|pwd|tree|cat|grep)\b",
            q,
        ):
            command = re.sub(r"^(ejecuta|corre|run)\s+", "", q).strip()
            command = re.sub(r"^comando\s+", "", command)
            return IntentResult("shell", {"command": command})

        # ------------------------------------------------------------
        # 3. DETECCIÓN DE DOCKER (comandos específicos, extrae el comando real)
        # ------------------------------------------------------------
        if re.search(r"\bdocker\b", q) and re.search(
            r"\b(ps|images|logs|status|inspect|start|stop|restart)\b", q
        ):
            return IntentResult(
                "docker",
                {"command": q},
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
