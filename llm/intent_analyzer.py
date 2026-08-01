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
        # 1. CREACIÓN DE PROYECTOS
        # ------------------------------------------------------------

        if re.search(
            r"\b(laravel|react|vue|django|fullstack)\b",
            q,
        ) and re.search(
            r"\b(crea|crear|genera|nuevo|proyecto)\b",
            q,
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
                params={
                    "framework": framework,
                    "name": name,
                },
                context_requirements=[
                    "engram",
                    "standards",
                    "documents",
                ],
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
        # 5. WRITE FILE
        # ------------------------------------------------------------

        if re.search(
            r"\b(crea|genera|escribe|guarda)\b",
            q,
        ) and re.search(
            r"\b(archivo|html|js|css|py|json|md|txt)\b",
            q,
        ):

            filepath = IntentAnalyzer._extract_file(query)

            return ExecutionPlan(
                original_task=query,
                intent="file_creation",
                objective="Crear archivo",
                agent="executor",
                skill="write_file",
                params={
                    "path": filepath,
                    "content": None,
                    "task": query,
                },
                context_requirements=["project"],
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
