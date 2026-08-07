from __future__ import annotations

import re
import unicodedata

from core.intent.models import IntentResult


class IntentDetectors:
    """
    Detectores puros de intención.

    No:

    - Ejecutan.
    - Crean planes.
    - Seleccionan agentes.
    """

    @staticmethod
    def detect(
        query: str,
    ) -> IntentResult | None:

        q = IntentDetectors.normalize(
            query,
        )

        detectors = [
            IntentDetectors.project_creation,
            IntentDetectors.refactor,
            IntentDetectors.debug,
            IntentDetectors.project_analysis,
            IntentDetectors.code_generation,
            IntentDetectors.testing,
            IntentDetectors.command_execution,
            IntentDetectors.docker,
            IntentDetectors.file_creation,
            IntentDetectors.spec,
            IntentDetectors.planning,
            IntentDetectors.documentation,
        ]

        for detector in detectors:

            result = detector(
                query,
                q,
            )

            if result:

                return result

        return None

    # ======================================================
    # Normalization
    # ======================================================

    @staticmethod
    def normalize(
        text: str,
    ) -> str:

        if not text:
            return ""

        normalized = (
            unicodedata.normalize(
                "NFKD",
                text,
            )
            .encode(
                "ascii",
                "ignore",
            )
            .decode()
        )

        return normalized.lower().strip()

    # ======================================================
    # Detectors
    # ======================================================

    @staticmethod
    def project_creation(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(laravel|react|vue|django|nestjs|spring)\b",
            q,
        ) and re.search(
            r"\b(crea|crear|nuevo|proyecto|genera)\b",
            q,
        ):

            return IntentResult(
                intent="project_creation",
                domain="project",
                category="creation",
                complexity="high",
                confidence=0.95,
                entities={
                    "framework": IntentDetectors.framework(q),
                    "name": IntentDetectors.project_name(query),
                },
                signals=[
                    "framework_detected",
                    "creation_keyword",
                ],
            )

        return None

    @staticmethod
    def code_generation(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(crea|genera|funcion|clase|componente|script)\b",
            q,
        ):

            return IntentResult(
                intent="code_generation",
                domain="code",
                category="development",
                confidence=0.85,
                entities={
                    "task": query,
                    "language": IntentDetectors.language(q),
                },
                signals=[
                    "code_keyword",
                ],
            )

        return None

    @staticmethod
    def refactor(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(refactor|optimiza|limpia|reestructura)\b",
            q,
        ):

            return IntentResult(
                intent="refactor",
                domain="code",
                category="maintenance",
                complexity="high",
                confidence=0.9,
                entities={
                    "task": query,
                },
                signals=[
                    "refactor_keyword",
                ],
            )

        return None

    @staticmethod
    def debug(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(error|bug|debug|falla|problema)\b",
            q,
        ):

            return IntentResult(
                intent="debug",
                domain="code",
                category="maintenance",
                confidence=0.85,
                entities={
                    "task": query,
                },
            )

        return None

    @staticmethod
    def testing(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(test|testing|prueba|unitario)\b",
            q,
        ):

            return IntentResult(
                intent="testing",
                domain="code",
                category="testing",
                entities={
                    "task": query,
                },
            )

        return None

    @staticmethod
    def command_execution(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(ejecuta|run|corre)\b",
            q,
        ):

            return IntentResult(
                intent="command_execution",
                domain="execution",
                category="command",
                entities={
                    "command": query,
                },
            )

        return None

    @staticmethod
    def docker(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if "docker" in q:

            return IntentResult(
                intent="docker",
                domain="execution",
                category="infrastructure",
                entities={
                    "command": query,
                },
            )

        return None

    @staticmethod
    def project_analysis(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if "analiza" in q and re.search(
            r"\b(proyecto|repo|codigo)\b",
            q,
        ):

            return IntentResult(
                intent="project_analysis",
                domain="analysis",
                category="project",
                complexity="high",
                entities={
                    "task": query,
                },
            )

        return None

    @staticmethod
    def file_creation(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(crea|genera|archivo)\b",
            q,
        ):

            return IntentResult(
                intent="file_creation",
                domain="file",
                category="creation",
                entities={
                    "path": IntentDetectors.file(query),
                    "task": query,
                },
            )

        return None

    @staticmethod
    def spec(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if "spec" in q or "especificacion" in q:

            return IntentResult(
                intent="spec",
                domain="planning",
                category="specification",
                complexity="high",
                entities={
                    "task": query,
                },
            )

        return None

    @staticmethod
    def planning(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(plan|roadmap|estrategia)\b",
            q,
        ):

            return IntentResult(
                intent="planning",
                domain="planning",
                category="strategy",
                complexity="high",
                entities={
                    "task": query,
                },
            )

        return None

    @staticmethod
    def documentation(
        query: str,
        q: str,
    ) -> IntentResult | None:

        if re.search(
            r"\b(readme|documenta|manual)\b",
            q,
        ):

            return IntentResult(
                intent="documentation",
                domain="documentation",
                category="generation",
                entities={
                    "task": query,
                },
            )

        return None

    # ======================================================
    # Extractors
    # ======================================================

    @staticmethod
    def framework(
        q: str,
    ) -> str:

        for item in (
            "laravel",
            "react",
            "vue",
            "django",
            "nestjs",
            "spring",
        ):

            if item in q:
                return item

        return "unknown"

    @staticmethod
    def language(
        q: str,
    ) -> str:

        if "python" in q:
            return "python"

        if "php" in q or "laravel" in q:
            return "php"

        if "typescript" in q:
            return "typescript"

        return "unknown"

    @staticmethod
    def project_name(
        query: str,
    ) -> str:

        match = re.search(
            r"(?:llamado|nombre)\s+(\w+)",
            query,
            re.I,
        )

        return match.group(1) if match else "mi_proyecto"

    @staticmethod
    def file(
        query: str,
    ) -> str:

        match = re.search(
            r"[\w\-]+\.(py|php|js|ts|tsx|json|md)",
            query,
            re.I,
        )

        return match.group(0) if match else "archivo.txt"
