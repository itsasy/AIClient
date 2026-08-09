from __future__ import annotations

import re
import unicodedata

from core.intent.models import IntentResult


class IntentDetectors:
    """
    Detectores puros de intención.

    Responsabilidades:
    - Analizar texto.
    - Detectar patrones semánticos.
    - Crear IntentResult.

    No:
    - Ejecutan acciones.
    - Crean ExecutionPlans.
    - Seleccionan agentes.
    - Seleccionan skills.
    """

    name = "intent_detectors"

    # ======================================================
    # Public API
    # ======================================================

    @classmethod
    def detect(cls, query: str) -> IntentResult | None:
        normalized = cls.normalize(query)

        detectors = (
            cls.project_creation,
            cls.refactor,
            cls.debug,
            cls.project_analysis,
            cls.code_generation,
            cls.testing,
            cls.command_execution,
            cls.docker,
            cls.file_creation,
            cls.spec,
            cls.planning,
            cls.documentation,
            cls.consolidation,  # Fase G
            cls.rollback,  # Fase G
            cls.analyze_metrics,  # Fase H
        )

        for detector in detectors:
            result = detector(query, normalized)
            if result:
                return result

        return None

    # ======================================================
    # Normalization
    # ======================================================

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""
        value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        return value.lower().strip()

    # ======================================================
    # Detectores existentes
    # ======================================================

    @classmethod
    def project_creation(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(laravel|react|vue|django|nestjs|spring)\b", q) and re.search(
            r"\b(crea|crear|nuevo|proyecto|genera)\b", q
        ):
            return IntentResult(
                intent="project_creation",
                domain="project",
                category="creation",
                complexity="high",
                confidence=0.95,
                entities={
                    "framework": cls.framework(q),
                    "name": cls.project_name(query),
                },
                signals=["framework_detected", "creation_keyword"],
            )
        return None

    @classmethod
    def code_generation(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(crea|genera|funcion|clase|componente|script)\b", q):
            return IntentResult(
                intent="code_generation",
                domain="code",
                category="development",
                confidence=0.85,
                entities={"task": query, "language": cls.language(q)},
                signals=["code_keyword"],
            )
        return None

    @classmethod
    def refactor(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(refactor|optimiza|limpia|reestructura)\b", q):
            return IntentResult(
                intent="refactor",
                domain="code",
                category="maintenance",
                complexity="high",
                confidence=0.9,
                entities={"task": query},
                signals=["refactor_keyword"],
            )
        return None

    @classmethod
    def debug(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(error|bug|debug|falla|problema)\b", q):
            return IntentResult(
                intent="debug",
                domain="code",
                category="maintenance",
                confidence=0.85,
                entities={"task": query},
                signals=["debug_keyword"],
            )
        return None

    @classmethod
    def testing(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(test|testing|prueba|unitario)\b", q):
            return IntentResult(
                intent="testing",
                domain="code",
                category="testing",
                entities={"task": query},
                signals=["testing_keyword"],
            )
        return None

    @classmethod
    def command_execution(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(ejecuta|run|corre)\b", q):
            return IntentResult(
                intent="command_execution",
                domain="execution",
                category="command",
                entities={"command": query},
                signals=["command_keyword"],
            )
        return None

    @classmethod
    def docker(cls, query: str, q: str) -> IntentResult | None:
        if "docker" in q:
            return IntentResult(
                intent="docker",
                domain="execution",
                category="infrastructure",
                entities={"command": query},
                signals=["docker_keyword"],
            )
        return None

    @classmethod
    def project_analysis(cls, query: str, q: str) -> IntentResult | None:
        if "analiza" in q and re.search(r"\b(proyecto|repo|codigo)\b", q):
            return IntentResult(
                intent="project_analysis",
                domain="analysis",
                category="project",
                complexity="high",
                entities={"task": query},
                signals=["analysis_keyword"],
            )
        return None

    @classmethod
    def file_creation(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(crea|genera|archivo)\b", q):
            return IntentResult(
                intent="file_creation",
                domain="file",
                category="creation",
                entities={"path": cls.file(query), "task": query},
                signals=["file_keyword"],
            )
        return None

    @classmethod
    def spec(cls, query: str, q: str) -> IntentResult | None:
        if "spec" in q or "especificacion" in q:
            return IntentResult(
                intent="spec",
                domain="planning",
                category="specification",
                complexity="high",
                entities={"task": query},
            )
        return None

    @classmethod
    def planning(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(plan|roadmap|estrategia)\b", q):
            return IntentResult(
                intent="planning",
                domain="planning",
                category="strategy",
                complexity="high",
                entities={"task": query},
            )
        return None

    @classmethod
    def documentation(cls, query: str, q: str) -> IntentResult | None:
        if re.search(r"\b(readme|documenta|manual)\b", q):
            return IntentResult(
                intent="documentation",
                domain="documentation",
                category="generation",
                entities={"task": query},
            )
        return None

    # ======================================================
    # NUEVOS DETECTORES (Fase G y H)
    # ======================================================

    @classmethod
    def consolidation(cls, query: str, q: str) -> IntentResult | None:
        if "consolidate" in q or "consolidacion" in q:
            return IntentResult(
                intent="consolidation",
                domain="memory",
                category="maintenance",
                entities={"task": query},
                signals=["consolidation_keyword"],
            )
        return None

    @classmethod
    def rollback(cls, query: str, q: str) -> IntentResult | None:
        if "rollback" in q:
            return IntentResult(
                intent="rollback",
                domain="memory",
                category="maintenance",
                entities={"task": query},
                signals=["rollback_keyword"],
            )
        return None

    @classmethod
    def analyze_metrics(cls, query: str, q: str) -> IntentResult | None:
        if "analyze" in q and ("metrics" in q or "rendimiento" in q):
            return IntentResult(
                intent="analyze_metrics",
                domain="analytics",
                category="analysis",
                entities={"task": query},
                signals=["analyze_keyword"],
            )
        return None

    # ======================================================
    # Extractores
    # ======================================================

    @staticmethod
    def framework(q: str) -> str:
        for fw in ("laravel", "react", "vue", "django", "nestjs", "spring"):
            if fw in q:
                return fw
        return "unknown"

    @staticmethod
    def language(q: str) -> str:
        if "python" in q:
            return "python"
        if "php" in q or "laravel" in q:
            return "php"
        if "typescript" in q:
            return "typescript"
        return "unknown"

    @staticmethod
    def project_name(query: str) -> str:
        match = re.search(r"(?:llamado|nombre)\s+(\w+)", query, re.I)
        return match.group(1) if match else "mi_proyecto"

    @staticmethod
    def file(query: str) -> str:
        match = re.search(r"[\w\-]+\.(py|php|js|ts|tsx|json|md|html)", query, re.I)
        return match.group(0) if match else "archivo.txt"
