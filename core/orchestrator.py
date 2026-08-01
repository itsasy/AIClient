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
    def analyze(query: str) -> ExecutionPlan:
        if not query:
            return ExecutionPlan(original_task="")

        q = query.lower().strip()
        logger.info("🔍 Analizando consulta: %s", query)

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

            logger.info("✅ Intención detectada: project_creation (%s)", framework)

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

            logger.info("✅ Intención detectada: command_execution")

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

            logger.info("✅ Intención detectada: docker_operation")

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

            logger.info("✅ Intención detectada: project_analysis")

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
        # 5. WRITE FILE (VERSIÓN MEJORADA)
        # ------------------------------------------------------------

        if re.search(r"\b(crea|genera|escribe|guarda|haz|crear|escribir)\b", q) and (
            re.search(r"\b(archivo|fichero)\b", q)
            or re.search(r"\b\w+\.(txt|html|js|css|py|json|md|xml|yaml|yml)\b", q)
        ):

            filepath = IntentAnalyzer._extract_file(query)

            logger.info("✅ Intención detectada: file_creation (archivo: %s)", filepath)

            return ExecutionPlan(
                original_task=query,
                intent="file_creation",
                objective=f"Crear archivo {filepath}",
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

            logger.info("✅ Intención detectada: spec_creation")

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

            logger.info("✅ Intención detectada: planning")

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
        # 8. GENERAL (FALLBACK)
        # ------------------------------------------------------------

        logger.info("ℹ️ Intención general (conversation)")

        return ExecutionPlan(
            original_task=query,
            intent="conversation",
            objective=query,
            agent="task",
            skill=None,
            params={},
            context_requirements=["engram"],
        )

    # ------------------------------------------------------------
    # MÉTODOS AUXILIARES
    # ------------------------------------------------------------

    @staticmethod
    def _extract_name(query: str) -> str:
        patterns = [
            r"llamado\s+(\w+)",
            r"nombre\s+(\w+)",
            r"proyecto\s+(\w+)$",
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)

        return "mi_proyecto"

    @staticmethod
    def _extract_file(query: str) -> str:
        # Buscar "archivo X" o "fichero X"
        match = re.search(r"(?:archivo|fichero)\s+['\"]?([\w\-\.]+)['\"]?", query, re.IGNORECASE)
        if match:
            return match.group(1)

        # Buscar cualquier palabra con extensión soportada
        match = re.search(
            r"\b([\w\-\.]+\.(txt|html|js|css|py|json|md|xml|yaml|yml))\b",
            query,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)

        return "archivo.txt"
