from __future__ import annotations

import logging
import re

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Convierte lenguaje natural en un ExecutionPlan.

    Este módulo solamente interpreta intención.
    No ejecuta tareas.
    """

    @staticmethod
    def analyze(
        query: str,
    ) -> ExecutionPlan:

        if not query:
            return ExecutionPlan(original_task="")

        q = query.lower().strip()

        plan = ExecutionPlan(original_task=query)

        # ======================================================
        # CREACIÓN DE PROYECTOS
        # ======================================================

        if (
            re.search(
                r"\b(laravel|react|vue|django|nestjs|spring)\b",
                q,
            )
            and re.search(
                r"\b(crea|crear|genera|nuevo|proyecto)\b",
                q,
            )
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

            plan.add_skill("plan")

            plan.execution_mode = "multi_step"

            for provider in [
                "project",
                "engram",
                "documents",
                "obsidian",
                "gentleman",
            ]:
                plan.add_context_requirement(provider)

            plan.params = {
                "framework": framework,
                "name": IntentAnalyzer._extract_name(query),
            }

            return plan

        # ======================================================
        # REFACTOR
        # ======================================================

        if re.search(
            r"\b(refactor|optimiza|mejora|limpia|reestructura)\b",
            q,
        ):

            plan.intent = "refactor"

            plan.intent_category = "code"

            plan.objective = "Refactorizar código existente"

            plan.agent = "coder"

            plan.add_skill("refactor_code")
            plan.add_skill("code")

            plan.add_context_requirement("project")
            plan.add_context_requirement("engram")
            plan.add_context_requirement("gentleman")

            return plan

        # ======================================================
        # DEBUG
        # ======================================================

        if re.search(
            r"\b(debug|error|bug|falla|fallo|problema)\b",
            q,
        ):

            plan.intent = "debug"

            plan.intent_category = "code"

            plan.objective = "Analizar y resolver problema técnico"

            plan.agent = "coder"

            plan.add_skill("debug")
            plan.add_skill("code")

            for provider in [
                "project",
                "engram",
                "documents",
                "gentleman",
            ]:
                plan.add_context_requirement(provider)

            return plan

        # ======================================================
        # GENERACIÓN DE CÓDIGO
        # ======================================================

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

            plan.add_skill("code")

            if language:
                plan.add_skill(language)

            for provider in [
                "project",
                "engram",
                "documents",
                "gentleman",
            ]:
                plan.add_context_requirement(provider)

            plan.params = {
                "task": query,
                "language": language,
            }

            return plan

        # ======================================================
        # TESTING
        # ======================================================

        if re.search(
            r"\b(test|testing|prueba|tests|unitario|unitaria)\b",
            q,
        ):

            plan.intent = "testing"

            plan.intent_category = "code"

            plan.objective = "Crear o analizar tests"

            plan.agent = "coder"

            plan.add_skill("testing")
            plan.add_skill("code")

            plan.add_context_requirement("project")
            plan.add_context_requirement("gentleman")

            return plan

        # ======================================================
        # SHELL
        # ======================================================

        if re.search(
            r"\b(ejecuta|run|corre)\b",
            q,
        ):

            command = re.sub(
                r"^(ejecuta|run|corre)\s+",
                "",
                query,
                flags=re.IGNORECASE,
            )

            plan.intent = "command_execution"

            plan.intent_category = "execution"

            plan.objective = "Ejecutar comando"

            plan.agent = "executor"

            plan.add_skill("shell")

            plan.add_context_requirement("project")

            plan.params = {
                "command": command,
            }

            return plan

        # ======================================================
        # DOCKER
        # ======================================================

        if "docker" in q:

            plan.intent = "docker"

            plan.intent_category = "execution"

            plan.objective = "Operación Docker"

            plan.agent = "executor"

            plan.add_skill("docker")

            plan.add_context_requirement("project")

            plan.params = {
                "command": query,
            }

            return plan

        # ======================================================
        # ANÁLISIS PROYECTO
        # ======================================================

        if re.search(
            r"\b(analiza|revisa|inspecciona|evalua|evalúa)\b",
            q,
        ) and re.search(
            r"\b(proyecto|repo|repositorio|codigo|código)\b",
            q,
        ):

            plan.intent = "project_analysis"

            plan.intent_category = "analysis"

            plan.objective = "Analizar proyecto"

            plan.agent = "architect"

            plan.add_skill("analyze_project")

            for provider in [
                "project",
                "engram",
                "documents",
                "obsidian",
                "gentleman",
            ]:
                plan.add_context_requirement(provider)

            return plan

        # ======================================================
        # ARCHIVOS
        # ======================================================

        if re.search(
            r"\b(crea|genera|escribe|guarda|archivo)\b",
            q,
        ):

            filepath = IntentAnalyzer._extract_file(query)

            content = IntentAnalyzer._extract_content(query)

            if content:

                plan.intent = "file_creation"

                plan.intent_category = "file"

                plan.objective = f"Crear {filepath}"

                plan.agent = "executor"

                plan.add_skill("write_file")

                plan.add_context_requirement("project")

                plan.params = {
                    "path": filepath,
                    "content": content,
                }

                return plan

            plan.intent = "file_generation"

            plan.intent_category = "planning"

            plan.objective = f"Generar {filepath}"

            plan.agent = "planner"

            plan.add_skill("plan")

            plan.execution_mode = "multi_step"

            for provider in [
                "project",
                "engram",
                "documents",
                "obsidian",
                "gentleman",
            ]:
                plan.add_context_requirement(provider)

            plan.params = {
                "filepath": filepath,
                "task": query,
            }

            return plan

        # ======================================================
        # SPEC
        # ======================================================

        if re.search(
            r"\b(spec|sdd|especificación|especificacion)\b",
            q,
        ):

            plan.intent = "spec"

            plan.intent_category = "planning"

            plan.objective = "Gestionar especificación"

            plan.agent = "planner"

            plan.add_skill("plan")

            plan.execution_mode = "multi_step"

            for provider in [
                "engram",
                "documents",
                "obsidian",
                "gentleman",
            ]:
                plan.add_context_requirement(provider)

            return plan

        # ======================================================
        # PLANIFICACIÓN
        # ======================================================

        if re.search(
            r"\b(planifica|plan|estrategia|roadmap|multi)\b",
            q,
        ):

            plan.intent = "planning"

            plan.intent_category = "planning"

            plan.objective = query

            plan.agent = "planner"

            plan.add_skill("plan")

            plan.execution_mode = "multi_step"

            for provider in [
                "engram",
                "documents",
                "obsidian",
                "gentleman",
            ]:
                plan.add_context_requirement(provider)

            return plan

        # ======================================================
        # DOCUMENTACIÓN
        # ======================================================

        if re.search(
            r"\b(documenta|documentación|readme|manual)\b",
            q,
        ):

            plan.intent = "documentation"

            plan.intent_category = "documentation"

            plan.objective = "Crear documentación"

            plan.agent = "writer"

            plan.add_skill("readme")

            plan.add_context_requirement("project")

            plan.add_context_requirement("documents")

            return plan

        # ======================================================
        # CONVERSACIÓN
        # ======================================================

        plan.intent = "conversation"

        plan.intent_category = "conversation"

        plan.objective = query

        plan.agent = "task"

        plan.add_skill("conversation")

        plan.add_context_requirement("engram")

        return plan

    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def _detect_framework(
        q: str,
    ) -> str:

        for item in [
            "laravel",
            "react",
            "vue",
            "django",
            "nestjs",
            "spring",
        ]:

            if item in q:
                return item

        return "fullstack"

    @staticmethod
    def _detect_language(
        q: str,
    ) -> str:

        mapping = {
            "python": "python",
            "php": "php",
            "typescript": "typescript",
            "javascript": "javascript",
            "react": "javascript",
            "vue": "javascript",
            "nestjs": "typescript",
            "laravel": "php",
        }

        for key, value in mapping.items():

            if key in q:
                return value

        return "python"

    @staticmethod
    def _extract_name(
        query: str,
    ) -> str:

        match = re.search(
            r"(?:llamado|nombre|proyecto)\s+(\w+)",
            query,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return "mi_proyecto"

    @staticmethod
    def _extract_file(
        query: str,
    ) -> str:

        match = re.search(
            r"([\w\-]+\.(html|css|js|ts|tsx|jsx|php|py|json|yaml|yml|md|txt|xml))",
            query,
            re.IGNORECASE,
        )

        return match.group(1) if match else "archivo.txt"

    @staticmethod
    def _extract_content(
        query: str,
    ) -> str | None:

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
