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
            # Detectar el framework específico
            framework = None
            if "react" in q:
                framework = "react"
            elif "vue" in q:
                framework = "vue"
            elif "django" in q:
                framework = "django"
            elif "fullstack" in q:
                framework = "fullstack"
            else:
                framework = "laravel"

            # Extraer el nombre
            name_match = re.search(r"llamado\s+(\S+)|nombre\s+(\S+)|proyecto\s+(\S+)$", q)
            if name_match:
                name = (
                    name_match.group(1)
                    or name_match.group(2)
                    or name_match.group(3)
                    or "mi_proyecto"
                )
            else:
                name = q.split()[-1] if q.split() else "mi_proyecto"

            # Si es Laravel, usar laravel_project. Para otros, usar full_project
            if framework == "laravel":
                return IntentResult("laravel_project", {"name": name})
            else:
                return IntentResult("full_project", {"framework": framework, "name": name})

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

        # ------------------------------------------------------------
        # 5. DETECCIÓN DE ESPECIFICACIONES (SDD)
        # ------------------------------------------------------------
        if re.search(r"\b(spec|especificación|sdd)\b", q) and re.search(
            r"\b(crea|genera|nuevo|ejecuta)\b", q
        ):
            return IntentResult("plan", {"original_task": query, "mode": "spec"})

        # ------------------------------------------------------------
        # 6. DETECCIÓN DE PLANIFICACIÓN AUTÓNOMA (genérica)
        # ------------------------------------------------------------
        if re.search(
            r"\b(plan|planifica|descompone|autónomo|autonomo|complejo|multi-paso|plan de acción)\b",
            q,
        ):
            return IntentResult("plan", {"original_task": query})

        # ------------------------------------------------------------
        # 7. DETECCIÓN DE INGESTA DE DOCUMENTOS
        # ------------------------------------------------------------
        if re.search(
            r"\b(ingiere|ingest|sube|carga|process|analiza)\b.*\b(documento|archivo|pdf|docx|imagen)\b",
            q,
        ):
            # Extraer el nombre del archivo (ej. "ingiere documento.pdf")
            file_match = re.search(
                r"\b([\w\-\.]+\.(pdf|docx|txt|png|jpg|jpeg))\b", q, re.IGNORECASE
            )
            if file_match:
                return IntentResult("ingest", {"filepath": file_match.group(1)})

        # ------------------------------------------------------------
        # 8. NUEVO: DETECCIÓN DE ESCRITURA DE ARCHIVOS (write_file)
        # ------------------------------------------------------------
        if re.search(
            r"\b(crea|genera|escribe|guarda|exporta)\b.*\b(archivo|fichero|código|codigo|html|js|css|py|json)\b",
            q,
            re.IGNORECASE,
        ):
            file_match = re.search(
                r"(?:archivo|fichero)\s+['\"]?([\w\-\.]+)['\"]?", q, re.IGNORECASE
            )
            if not file_match:
                ext_match = re.search(
                    r"\b([\w\-\.]+\.(html|js|css|py|json|txt|md|xml|yaml|yml))\b",
                    q,
                    re.IGNORECASE,
                )
                if ext_match:
                    filepath = ext_match.group(1)
                else:
                    filepath = "output.html"
            else:
                filepath = file_match.group(1)

            return IntentResult("write_file", {"path": filepath, "content": None})

        # ------------------------------------------------------------
        # 9. SIN INTENCIÓN DETECTADA
        # ------------------------------------------------------------
        return IntentResult(None, None)
