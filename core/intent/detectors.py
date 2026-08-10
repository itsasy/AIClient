from __future__ import annotations

import re
import unicodedata

from core.intent.models import IntentResult


class IntentDetectors:
    """
    Detectores deterministas de intención.

    Responsabilidades:

    - Normalizar la consulta.
    - Detectar patrones.
    - Extraer entidades.
    - Crear IntentResult.

    No:

    - ejecutan acciones;
    - construyen ExecutionPlans;
    - seleccionan agentes;
    - seleccionan skills;
    - gestionan contexto.
    """

    name = "intent_detectors"

    # =========================================================
    # Public API
    # =========================================================

    @classmethod
    def detect(
        cls,
        query: str,
    ) -> IntentResult | None:

        normalized = cls.normalize(query)

        if not normalized:
            return None

        detectors = (
            cls.project_creation,
            cls.project_analysis,
            cls.docker,
            cls.command_execution,
            cls.file_creation,
            cls.refactor,
            cls.debug,
            cls.testing,
            cls.spec,
            cls.planning,
            cls.documentation,
            cls.consolidation,
            cls.rollback,
            cls.analyze_metrics,
            cls.code_generation,
        )

        for detector in detectors:
            result = detector(
                query,
                normalized,
            )

            if result:
                return result

        return None

    # =========================================================
    # Normalization
    # =========================================================

    @staticmethod
    def normalize(
        text: str,
    ) -> str:

        if not text:
            return ""

        value = (
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

        return " ".join(value.lower().strip().split())

    # =========================================================
    # Project creation
    # =========================================================

    @classmethod
    def project_creation(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        framework_pattern = (
            r"\b("
            r"laravel|"
            r"react|"
            r"vue|"
            r"django|"
            r"nestjs|"
            r"spring|"
            r"fastapi|"
            r"nextjs|"
            r"next"
            r")\b"
        )

        creation_pattern = (
            r"\b("
            r"crear|"
            r"crea|"
            r"nuevo|"
            r"nueva|"
            r"generar|"
            r"genera|"
            r"crear un proyecto|"
            r"crear proyecto"
            r")\b"
        )

        if not re.search(framework_pattern, q):
            return None

        if not re.search(creation_pattern, q):
            return None

        return IntentResult(
            intent="project_creation",
            domain="project",
            category="creation",
            complexity="high",
            confidence=0.95,
            entities={
                "framework": cls.framework(q),
                "name": cls.project_name(query),
                "task": query,
            },
            signals=[
                "framework_detected",
                "creation_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Project analysis
    # =========================================================

    @classmethod
    def project_analysis(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        analysis = re.search(
            r"\b("
            r"analiza|"
            r"analizar|"
            r"revisa|"
            r"revisar|"
            r"inspecciona|"
            r"inspeccionar|"
            r"evalua|"
            r"evaluar"
            r")\b",
            q,
        )

        target = re.search(
            r"\b(" r"proyecto|" r"repo|" r"repositorio|" r"codigo|" r"arquitectura" r")\b",
            q,
        )

        if not analysis or not target:
            return None

        return IntentResult(
            intent="project_analysis",
            domain="analysis",
            category="project",
            complexity="high",
            confidence=0.92,
            entities={
                "task": query,
            },
            signals=[
                "analysis_keyword",
                "project_target",
            ],
            original_query=query,
        )

    # =========================================================
    # Docker
    # =========================================================

    @classmethod
    def docker(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(r"\bdocker\b", q):
            return None

        return IntentResult(
            intent="docker",
            domain="execution",
            category="infrastructure",
            complexity="normal",
            confidence=0.95,
            entities={
                "command": query,
            },
            signals=[
                "docker_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Command execution
    # =========================================================

    @classmethod
    def command_execution(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(" r"ejecuta|" r"ejecutar|" r"run|" r"corre|" r"correr|" r"lanza|" r"lanzar" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="command_execution",
            domain="execution",
            category="command",
            confidence=0.90,
            entities={
                "command": query,
            },
            signals=[
                "command_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # File creation
    # =========================================================

    @classmethod
    def file_creation(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        creation = re.search(
            r"\b(" r"crear|" r"crea|" r"generar|" r"genera" r")\b",
            q,
        )

        file_keyword = re.search(
            r"\b(" r"archivo|" r"fichero|" r"file" r")\b",
            q,
        )

        extension = re.search(
            r"\.\w{1,10}\b",
            q,
        )

        if not creation:
            return None

        if not file_keyword and not extension:
            return None

        return IntentResult(
            intent="file_creation",
            domain="file",
            category="creation",
            confidence=0.92,
            entities={
                "path": cls.file(query),
                "task": query,
            },
            signals=[
                "file_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Refactor
    # =========================================================

    @classmethod
    def refactor(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b("
            r"refactor|"
            r"refactoriza|"
            r"refactorizar|"
            r"optimiza|"
            r"optimizar|"
            r"reestructura|"
            r"reestructurar|"
            r"limpia|"
            r"limpiar"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="refactor",
            domain="code",
            category="maintenance",
            complexity="high",
            confidence=0.92,
            entities={
                "task": query,
            },
            signals=[
                "refactor_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Debug
    # =========================================================

    @classmethod
    def debug(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b("
            r"error|"
            r"bug|"
            r"debug|"
            r"falla|"
            r"fallo|"
            r"problema|"
            r"excepcion|"
            r"exception"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="debug",
            domain="code",
            category="maintenance",
            complexity="normal",
            confidence=0.88,
            entities={
                "task": query,
            },
            signals=[
                "debug_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Testing
    # =========================================================

    @classmethod
    def testing(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b("
            r"test|"
            r"testing|"
            r"tests|"
            r"prueba|"
            r"pruebas|"
            r"unitario|"
            r"unitaria|"
            r"integracion"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="testing",
            domain="code",
            category="testing",
            confidence=0.88,
            entities={
                "task": query,
            },
            signals=[
                "testing_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Specification
    # =========================================================

    @classmethod
    def spec(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(" r"spec|" r"specification|" r"especificacion|" r"especificación" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="spec",
            domain="planning",
            category="specification",
            complexity="high",
            confidence=0.92,
            entities={
                "task": query,
            },
            signals=[
                "spec_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Planning
    # =========================================================

    @classmethod
    def planning(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(" r"plan|" r"planifica|" r"planificar|" r"roadmap|" r"estrategia" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="planning",
            domain="planning",
            category="strategy",
            complexity="high",
            confidence=0.90,
            entities={
                "task": query,
            },
            signals=[
                "planning_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Documentation
    # =========================================================

    @classmethod
    def documentation(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(" r"readme|" r"documenta|" r"documentar|" r"documentacion|" r"manual" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="documentation",
            domain="documentation",
            category="generation",
            confidence=0.90,
            entities={
                "task": query,
            },
            signals=[
                "documentation_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Consolidation
    # =========================================================

    @classmethod
    def consolidation(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(" r"consolidate|" r"consolidacion|" r"consolidación|" r"consolidar" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="consolidation",
            domain="memory",
            category="maintenance",
            confidence=0.90,
            entities={
                "task": query,
            },
            signals=[
                "consolidation_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Rollback
    # =========================================================

    @classmethod
    def rollback(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(" r"rollback|" r"revertir|" r"revert|" r"deshacer" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="rollback",
            domain="memory",
            category="maintenance",
            confidence=0.90,
            entities={
                "task": query,
            },
            signals=[
                "rollback_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Metrics
    # =========================================================

    @classmethod
    def analyze_metrics(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        analyze = re.search(
            r"\b(" r"analiza|" r"analizar|" r"analyze|" r"analizar" r")\b",
            q,
        )

        metrics = re.search(
            r"\b(" r"metricas|" r"métricas|" r"metrics|" r"rendimiento|" r"performance" r")\b",
            q,
        )

        if not analyze or not metrics:
            return None

        return IntentResult(
            intent="analyze_metrics",
            domain="analytics",
            category="analysis",
            confidence=0.88,
            entities={
                "task": query,
            },
            signals=[
                "metrics_keyword",
                "analysis_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Code generation
    # =========================================================

    @classmethod
    def code_generation(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        creation = re.search(
            r"\b(" r"crea|" r"crear|" r"genera|" r"generar|" r"implementa|" r"implementar" r")\b",
            q,
        )

        code_target = re.search(
            r"\b("
            r"funcion|"
            r"función|"
            r"clase|"
            r"componente|"
            r"script|"
            r"endpoint|"
            r"servicio|"
            r"controller|"
            r"controlador|"
            r"middleware|"
            r"repository|"
            r"repositorio"
            r")\b",
            q,
        )

        if not creation or not code_target:
            return None

        return IntentResult(
            intent="code_generation",
            domain="code",
            category="development",
            confidence=0.85,
            entities={
                "task": query,
                "language": cls.language(q),
            },
            signals=[
                "code_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Extractors
    # =========================================================

    @staticmethod
    def framework(q: str) -> str:

        frameworks = (
            "laravel",
            "react",
            "vue",
            "django",
            "nestjs",
            "spring",
            "fastapi",
            "nextjs",
            "next",
        )

        for framework in frameworks:
            if re.search(
                rf"\b{re.escape(framework)}\b",
                q,
            ):
                return framework

        return "unknown"

    @staticmethod
    def language(q: str) -> str:

        if re.search(r"\bpython\b", q):
            return "python"

        if re.search(r"\b(php|laravel)\b", q):
            return "php"

        if re.search(
            r"\b(typescript|ts)\b",
            q,
        ):
            return "typescript"

        if re.search(
            r"\b(javascript|js)\b",
            q,
        ):
            return "javascript"

        if re.search(
            r"\b(java|spring)\b",
            q,
        ):
            return "java"

        return "unknown"

    @staticmethod
    def project_name(
        query: str,
    ) -> str:

        patterns = (
            r"(?:llamado|llamada|nombre)\s+([A-Za-z0-9_-]+)",
            r"(?:proyecto)\s+([A-Za-z0-9_-]+)",
        )

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
    def file(
        query: str,
    ) -> str:

        match = re.search(
            r"([A-Za-z0-9_.\\/-]+\.(?:py|php|js|ts|tsx|jsx|json|md|html|css|yaml|yml|toml))\b",
            query,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return "archivo.txt"
