from __future__ import annotations

import re
import logging

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Convierte una solicitud del usuario en un ExecutionPlan.

    Este componente es el único responsable de interpretar
    la intención inicial.

    Ningún Router ni Agent debe volver a analizar la intención.
    """

    @staticmethod
    def analyze(
        query: str,
    ) -> ExecutionPlan:

        if not query:
            return ExecutionPlan(original_task="")

        q = query.lower().strip()

        # ------------------------------------------------------------
        # 1. CREACIÓN DE PROYECTOS (solo si NO es generación de código)
        # ------------------------------------------------------------
        if (
            re.search(r"\b(laravel|react|vue|django|fullstack)\b", q)
            and re.search(r"\b(proyecto|crea|crear|genera|nuevo)\b", q)
            and not re.search(r"\b(componente|funcion|función|clase|script|hook)\b", q)
        ):

            framework = (
                "react"
                if "react" in q
                else (
                    "vue"
                    if "vue" in q
                    else "django" if "django" in q else "laravel" if "laravel" in q else "fullstack"
                )
            )

            name = IntentAnalyzer._extract_name(query)
            skill = "laravel_project" if framework == "laravel" else "full_project"

            return ExecutionPlan(
                original_task=query,
                intent="project_creation",
                objective=f"Crear proyecto {framework}",
                agent="executor",
                skill=skill,
                params={"framework": framework, "name": name},
                context_requirements=["engram", "standards", "documents", "gentleman"],
            )

        # ------------------------------------------------------------
        # 2. GENERACIÓN DE CÓDIGO (componentes, funciones, clases)
        # ------------------------------------------------------------
        if re.search(r"\b(componente|funcion|función|clase|script|genera|crea)\b", q) and re.search(
            r"\b(react|vue|python|javascript|typescript|js|ts|php)\b", q
        ):

            # Detectar lenguaje
            language = "javascript"
            if "python" in q:
                language = "python"
            elif "typescript" in q or "ts" in q:
                language = "typescript"
            elif "php" in q:
                language = "php"
            elif "vue" in q:
                language = "vue"
            elif "react" in q:
                language = "react"

            context_requirements = ["engram", "gentleman"]
            if "proyecto" in q or "repo" in q:
                context_requirements.append("project")

            return ExecutionPlan(
                original_task=query,
                intent="code_generation",
                objective="Generar código siguiendo mejores prácticas",
                agent="coder",
                skill="code",
                params={"task": query, "language": language},
                context_requirements=context_requirements,
            )

        # ------------------------------------------------------------
        # 2. EJECUCIÓN DE COMANDOS
        # ------------------------------------------------------------

        if re.search(
            r"\b(ejecuta|corre|run)\b",
            q,
        ):

            command = re.sub(
                r"^(ejecuta|corre|run)\s+",
                "",
                q,
            )

            return ExecutionPlan(
                original_task=query,
                intent="command_execution",
                objective="Ejecutar comando",
                agent="executor",
                skill="shell",
                params={"command": command},
                context_requirements=["project"],
            )

        # ------------------------------------------------------------
        # 3. DOCKER
        # ------------------------------------------------------------

        if "docker" in q and re.search(
            r"\b(ps|images|logs|start|stop|restart)\b",
            q,
        ):

            return ExecutionPlan(
                original_task=query,
                intent="docker_operation",
                objective="Ejecutar operación Docker",
                agent="executor",
                skill="docker",
                params={"command": query},
                context_requirements=["project"],
            )

        # ------------------------------------------------------------
        # 4. ANALIZAR PROYECTO
        # ------------------------------------------------------------

        if re.search(
            r"\b(analiza|revisa)\b",
            q,
        ) and re.search(
            r"\b(proyecto|repo|codigo|código)\b",
            q,
        ):

            return ExecutionPlan(
                original_task=query,
                intent="project_analysis",
                objective="Analizar proyecto",
                agent="architect",
                skill="analyze_project",
                params={},
                context_requirements=[
                    "project",
                    "engram",
                    "standards",
                ],
            )

        # ------------------------------------------------------------
        # 5. ESCRITURA DE ARCHIVOS
        # ------------------------------------------------------------
        if re.search(r"\b(crea|genera|escribe|guarda|exporta)\b", q) and re.search(
            r"\b(archivo|html|js|css|py|json|md|txt|xml|yaml|yml)\b", q
        ):
            # Extraer nombre de archivo
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
                    filepath = "archivo.txt"
            else:
                filepath = file_match.group(1)

            # 5b. ¿El usuario proporcionó contenido explícito?
            # Buscar "con el texto", "contenido", "contenido:", o texto entre comillas
            explicit_content = None

            # Patrón 1: "con el texto '...'"
            content_match = re.search(r"con\s+el\s+texto\s+['\"](.+?)['\"]", q, re.IGNORECASE)
            if content_match:
                explicit_content = content_match.group(1)

            # Patrón 2: "contenido:'...'"
            if not explicit_content:
                content_match = re.search(r"contenido\s*:\s*['\"](.+?)['\"]", q, re.IGNORECASE)
                if content_match:
                    explicit_content = content_match.group(1)

            # Patrón 3: "que diga '...'"
            if not explicit_content:
                content_match = re.search(r"que\s+diga\s+['\"](.+?)['\"]", q, re.IGNORECASE)
                if content_match:
                    explicit_content = content_match.group(1)

            # 5c. Si hay contenido explícito → write_file directo
            if explicit_content:
                return ExecutionPlan(
                    original_task=query,
                    intent="file_creation",
                    objective=f"Crear archivo {filepath} con contenido explícito",
                    agent="executor",
                    skill="write_file",
                    params={"path": filepath, "content": explicit_content},
                    context_requirements=["project"],
                    execution_mode="single",
                )

            # 5d. Si NO hay contenido explícito → planificar generación de contenido
            # El PlannerAgent generará el contenido y luego llamará a write_file
            return ExecutionPlan(
                original_task=query,
                intent="file_creation_with_generation",
                objective=f"Crear archivo {filepath} con contenido generado",
                agent="planner",
                skill="plan",
                params={
                    "filepath": filepath,
                    "task_description": query,
                },
                context_requirements=["engram", "project", "obsidian"],
                execution_mode="multi_step",
            )

        # ------------------------------------------------------------
        # 6. SPEC / SDD
        # ------------------------------------------------------------

        if re.search(
            r"\b(spec|sdd|especificacion|especificación)\b",
            q,
        ) and re.search(
            r"\b(crea|genera|nuevo)\b",
            q,
        ):

            return ExecutionPlan(
                original_task=query,
                intent="spec_creation",
                objective="Crear especificación",
                agent="planner",
                skill="plan",
                params={"mode": "spec"},
                context_requirements=[
                    "engram",
                    "obsidian",
                    "standards",
                ],
            )

        # ------------------------------------------------------------
        # 7. PLANIFICACIÓN
        # ------------------------------------------------------------

        if re.search(
            r"\b(plan|planifica|complejo|multi-paso)\b",
            q,
        ):

            return ExecutionPlan(
                original_task=query,
                intent="planning",
                objective="Crear plan de ejecución",
                agent="planner",
                skill="plan",
                params={},
                context_requirements=[
                    "engram",
                    "obsidian",
                ],
            )

        # ------------------------------------------------------------
        # 8. GENERAL
        # ------------------------------------------------------------

        return ExecutionPlan(
            original_task=query,
            intent="conversation",
            objective=query,
            agent="task",
            skill=None,
            params={},
            context_requirements=["engram"],
        )

    @staticmethod
    def _extract_name(query: str) -> str:

        patterns = [
            r"llamado\s+(\w+)",
            r"nombre\s+(\w+)",
            r"proyecto\s+(\w+)$",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                query,
                re.IGNORECASE,
            )

            if match:
                return match.group(1)

        return "mi_proyecto"

    @staticmethod
    def _extract_file(query: str) -> str:

        match = re.search(
            r"([\w\-]+\.(html|js|css|py|json|md|txt))",
            query,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return "archivo.txt"
