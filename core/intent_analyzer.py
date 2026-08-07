from __future__ import annotations

import logging
import re

from typing import Any

logger = logging.getLogger(__name__)


class IntentAnalyzer:
    """
    Analiza lenguaje natural y devuelve intención.

    Responsabilidades:

    - Detectar intención.
    - Detectar dominio.
    - Detectar complejidad.
    - Extraer entidades relevantes.

    No:

    - Construye ExecutionPlan.
    - Selecciona Agents.
    - Selecciona Skills.
    - Ejecuta tareas.
    - Gestiona contexto.
    """

    # ======================================================
    # Public API
    # ======================================================

    @staticmethod
    def analyze(
        query: str,
    ) -> dict[str, Any]:

        if not query:

            return {
                "intent": "conversation",
                "domain": "conversation",
                "complexity": "normal",
                "entities": {},
            }

        q = query.lower().strip()

        # ==================================================
        # PROJECT CREATION
        # ==================================================

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

            return {
                "intent": "project_creation",
                "domain": "project",
                "complexity": "high",
                "entities": {
                    "framework": IntentAnalyzer._detect_framework(q),
                    "name": IntentAnalyzer._extract_name(query),
                },
            }

        # ==================================================
        # REFACTOR
        # ==================================================

        if re.search(
            r"\b(refactor|optimiza|mejora|limpia|reestructura)\b",
            q,
        ):

            return {
                "intent": "refactor",
                "domain": "code",
                "complexity": "high",
                "entities": {
                    "task": query,
                },
            }

        # ==================================================
        # DEBUG
        # ==================================================

        if re.search(
            r"\b(debug|error|bug|falla|fallo|problema)\b",
            q,
        ):

            return {
                "intent": "debug",
                "domain": "code",
                "complexity": "normal",
                "entities": {
                    "task": query,
                },
            }

        # ==================================================
        # CODE GENERATION
        # ==================================================

        if re.search(
            r"\b(crea|genera|funcion|función|clase|componente|script)\b",
            q,
        ) and re.search(
            r"\b(python|php|typescript|javascript|react|vue|nestjs|laravel)\b",
            q,
        ):

            return {
                "intent": "code_generation",
                "domain": "code",
                "complexity": "normal",
                "entities": {
                    "language": IntentAnalyzer._detect_language(q),
                    "task": query,
                },
            }

        # ==================================================
        # TESTING
        # ==================================================

        if re.search(
            r"\b(test|testing|prueba|tests|unitario|unitaria)\b",
            q,
        ):

            return {
                "intent": "testing",
                "domain": "code",
                "complexity": "normal",
                "entities": {
                    "task": query,
                },
            }

        # ==================================================
        # COMMAND EXECUTION
        # ==================================================

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

            return {
                "intent": "command_execution",
                "domain": "execution",
                "complexity": "normal",
                "entities": {
                    "command": command,
                },
            }

        # ==================================================
        # DOCKER
        # ==================================================

        if "docker" in q:

            return {
                "intent": "docker",
                "domain": "execution",
                "complexity": "normal",
                "entities": {
                    "command": query,
                },
            }

        # ==================================================
        # PROJECT ANALYSIS
        # ==================================================

        if re.search(
            r"\b(analiza|revisa|inspecciona|evalua|evalúa)\b",
            q,
        ) and re.search(
            r"\b(proyecto|repo|repositorio|codigo|código)\b",
            q,
        ):

            return {
                "intent": "project_analysis",
                "domain": "analysis",
                "complexity": "high",
                "entities": {
                    "task": query,
                },
            }

        # ==================================================
        # FILE CREATION
        # ==================================================

        if re.search(
            r"\b(crea|genera|escribe|guarda|archivo)\b",
            q,
        ):

            filepath = IntentAnalyzer._extract_file(query)

            content = IntentAnalyzer._extract_content(query)

            return {
                "intent": ("file_creation" if content else "file_generation"),
                "domain": "file",
                "complexity": ("normal" if content else "high"),
                "entities": {
                    "path": filepath,
                    "content": content,
                    "task": query,
                },
            }

        # ==================================================
        # SPEC
        # ==================================================

        if re.search(
            r"\b(spec|sdd|especificación|especificacion)\b",
            q,
        ):

            return {
                "intent": "spec",
                "domain": "planning",
                "complexity": "high",
                "entities": {
                    "task": query,
                },
            }

        # ==================================================
        # PLANNING
        # ==================================================

        if re.search(
            r"\b(planifica|plan|estrategia|roadmap|multi)\b",
            q,
        ):

            return {
                "intent": "planning",
                "domain": "planning",
                "complexity": "high",
                "entities": {
                    "task": query,
                },
            }

        # ==================================================
        # DOCUMENTATION
        # ==================================================

        if re.search(
            r"\b(documenta|documentación|readme|manual)\b",
            q,
        ):

            return {
                "intent": "documentation",
                "domain": "documentation",
                "complexity": "normal",
                "entities": {
                    "task": query,
                },
            }

        # ==================================================
        # DEFAULT
        # ==================================================

        return {
            "intent": "conversation",
            "domain": "conversation",
            "complexity": "normal",
            "entities": {
                "task": query,
            },
        }

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
