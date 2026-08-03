from __future__ import annotations

import logging
import re

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Convierte lenguaje natural en un ExecutionPlan.

    Este módulo NO ejecuta nada.
    Sólo interpreta la intención del usuario.
    """

    @staticmethod
    def analyze(query: str) -> ExecutionPlan:

        if not query:
            return ExecutionPlan(original_task="")

        q = query.lower().strip()

        plan = ExecutionPlan(
            original_task=query,
        )

        # ==========================================================
        # CREACIÓN DE PROYECTOS
        # ==========================================================

        if (
            re.search(r"\b(laravel|react|vue|django|nestjs|spring)\b", q)
            and re.search(r"\b(crea|crear|genera|nuevo|proyecto)\b", q)
            and not re.search(
                r"\b(componente|funcion|función|clase|script|hook)\b",
                q,
            )
        ):

            framework = IntentAnalyzer._detect_framework(q)

            plan.intent = "project_creation"
            plan.intent_category = "project"

            plan.objective = f"Crear proyecto {framework}"

            plan.agent = "planner"

            plan.skill = "plan"

            plan.execution_mode = "multi_step"

            plan.context_requirements = [
                "project",
                "engram",
                "obsidian",
                "documents",
                "gentleman",
            ]

            plan.params = {
                "framework": framework,
                "name": IntentAnalyzer._extract_name(query),
            }

            return plan

        # ==========================================================
        # GENERACIÓN DE CÓDIGO
        # ==========================================================

        if re.search(
            r"\b(crea|genera|funcion|función|clase|componente|script)\b",
            q,
        ) and re.search(
            r"\b(python|php|typescript|javascript|react|vue|nestjs|laravel)\b",
            q,
        ):

            language = IntentAnalyzer._detect_language(q)

            plan.intent = "code_generation"
            plan.intent_category = "code"

            plan.objective = "Generar código"

            plan.agent = "coder"

            plan.skill = "code"

            plan.context_requirements = [
                "project",
                "engram",
                "gentleman",
                "documents",
            ]

            plan.params = {
                "task": query,
                "language": language,
            }

            return plan

        # ==========================================================
        # SHELL
        # ==========================================================

        if re.search(r"\b(ejecuta|run|corre)\b", q):

            command = re.sub(
                r"^(ejecuta|run|corre)\s+",
                "",
                query,
                flags=re.IGNORECASE,
            )

            plan.intent = "command_execution"
            plan.intent_category = "execution"

            plan.agent = "executor"

            plan.skill = "shell"

            plan.objective = "Ejecutar comando"

            plan.context_requirements = [
                "project",
            ]

            plan.params = {
                "command": command,
            }

            return plan

        # ==========================================================
        # DOCKER
        # ==========================================================

        if "docker" in q:

            plan.intent = "docker"

            plan.intent_category = "execution"

            plan.agent = "executor"

            plan.skill = "docker"

            plan.objective = "Operación Docker"

            plan.context_requirements = [
                "project",
            ]

            plan.params = {
                "command": query,
            }

            return plan

        # ==========================================================
        # ANALIZAR PROYECTO
        # ==========================================================

        if re.search(r"\b(analiza|revisa|inspecciona|evalua|evalúa)\b", q) and re.search(
            r"\b(proyecto|repo|repositorio|codigo|código)\b", q
        ):

            plan.intent = "project_analysis"

            plan.intent_category = "analysis"

            plan.agent = "architect"

            plan.skill = "analyze_project"

            plan.objective = "Analizar proyecto"

            plan.execution_mode = "single"

            plan.context_requirements = [
                "project",
                "engram",
                "documents",
                "gentleman",
                "obsidian",
            ]

            return plan

        # ==========================================================
        # CREACIÓN DE ARCHIVOS
        # ==========================================================

        if re.search(
            r"\b(crea|genera|escribe|guarda|archivo)\b",
            q,
        ):

            filepath = IntentAnalyzer._extract_file(query)

            explicit = IntentAnalyzer._extract_content(query)

            if explicit:

                plan.intent = "file_creation"

                plan.intent_category = "file"

                plan.agent = "executor"

                plan.skill = "write_file"

                plan.objective = f"Crear {filepath}"

                plan.context_requirements = [
                    "project",
                ]

                plan.params = {
                    "path": filepath,
                    "content": explicit,
                }

                return plan

            plan.intent = "file_generation"

            plan.intent_category = "planning"

            plan.agent = "planner"

            plan.skill = "plan"

            plan.execution_mode = "multi_step"

            plan.objective = f"Generar {filepath}"

            plan.context_requirements = [
                "project",
                "engram",
                "documents",
                "gentleman",
                "obsidian",
            ]

            plan.params = {
                "filepath": filepath,
                "task": query,
            }

            return plan

        # ==========================================================
        # SPEC
        # ==========================================================

        if re.search(r"\b(spec|sdd|especificación|especificacion)\b", q):

            plan.intent = "spec"

            plan.intent_category = "planning"

            plan.agent = "planner"

            plan.skill = "plan"

            plan.execution_mode = "multi_step"

            plan.objective = "Gestionar especificación"

            plan.context_requirements = [
                "engram",
                "documents",
                "obsidian",
                "gentleman",
            ]

            return plan

        # ==========================================================
        # PLANIFICACIÓN
        # ==========================================================

        if re.search(
            r"\b(planifica|plan|estrategia|roadmap|multi)\b",
            q,
        ):

            plan.intent = "planning"

            plan.intent_category = "planning"

            plan.agent = "planner"

            plan.skill = "plan"

            plan.execution_mode = "multi_step"

            plan.objective = query

            plan.context_requirements = [
                "engram",
                "documents",
                "obsidian",
                "gentleman",
            ]

            return plan

        # ==========================================================
        # CONVERSACIÓN GENERAL
        # ==========================================================

        plan.intent = "conversation"

        plan.intent_category = "conversation"

        plan.agent = "task"

        plan.skill = None

        plan.objective = query

        plan.context_requirements = [
            "engram",
            "documents",
            "obsidian",
        ]

        return plan

    # ==============================================================
    # Helpers
    # ==============================================================

    @staticmethod
    def _detect_framework(q: str) -> str:

        frameworks = [
            "laravel",
            "react",
            "vue",
            "django",
            "nestjs",
            "spring",
        ]

        for fw in frameworks:
            if fw in q:
                return fw

        return "fullstack"

    @staticmethod
    def _detect_language(q: str) -> str:

        mapping = {
            "python": "python",
            "php": "php",
            "typescript": "typescript",
            "javascript": "javascript",
            "react": "react",
            "vue": "vue",
            "nestjs": "typescript",
            "laravel": "php",
        }

        for key, value in mapping.items():
            if key in q:
                return value

        return "python"

    @staticmethod
    def _extract_name(query: str) -> str:

        patterns = [
            r"llamado\s+(\w+)",
            r"nombre\s+(\w+)",
            r"proyecto\s+(\w+)",
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
            r"([\w\-]+\.(html|css|js|ts|tsx|jsx|php|py|json|yaml|yml|md|txt|xml))",
            query,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return "archivo.txt"

    @staticmethod
    def _extract_content(query: str) -> str | None:

        patterns = [
            r'con\s+el\s+texto\s+"(.+?)"',
            r"con\s+el\s+texto\s+'(.+?)'",
            r'contenido\s*:\s*"(.+?)"',
            r"contenido\s*:\s*'(.+?)'",
            r'que\s+diga\s+"(.+?)"',
            r"que\s+diga\s+'(.+?)'",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                query,
                re.IGNORECASE,
            )

            if match:
                return match.group(1)

        return None
