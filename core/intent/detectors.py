from __future__ import annotations

import re
import unicodedata

from core.intent.models import IntentResult


class IntentDetectors:
    """
    Detectores deterministas de intención.
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
            cls.module_scaffold,
            cls.ui_scaffold,
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
            result = detector(query, normalized)
            if result:
                return result

        return None

    # =========================================================
    # Normalization
    # =========================================================

    @staticmethod
    def normalize(text: str) -> str:
        if not text:
            return ""

        value = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
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
            r"\b(" r"laravel|react|vue|django|nestjs|spring|fastapi|nextjs|next" r")\b"
        )
        creation_pattern = (
            r"\b("
            r"crear|crea|nuevo|nueva|generar|genera|"
            r"crear un proyecto|crear proyecto"
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
            signals=["framework_detected", "creation_keyword"],
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
            r"\b(analiza|analizar|revisa|revisar|inspecciona|inspeccionar|evalua|evaluar)\b",
            q,
        )
        target = re.search(
            r"\b(proyecto|repo|repositorio|codigo|arquitectura)\b",
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
            entities={"task": query},
            signals=["analysis_keyword", "project_target"],
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
            entities={"command": query},
            signals=["docker_keyword"],
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
            r"\b(ejecuta|ejecutar|run|corre|correr|lanza|lanzar)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="command_execution",
            domain="execution",
            category="command",
            confidence=0.90,
            entities={"command": query},
            signals=["command_keyword"],
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
            r"\b(crear|crea|generar|genera|escribe|escribir)\b",
            q,
        )
        if not creation:
            return None

        file_keyword = re.search(r"\b(archivo|fichero|file)\b", q)
        extension = re.search(r"\.\w{1,10}\b", q)
        traversal = re.search(
            r"(\.\./)+[^\s\"']+|(?:^|\s)/[^\s\"']+|(?:^|\s)\.\./[^\s\"']+",
            query,
        )

        if not file_keyword and not extension and not traversal:
            return None

        path = cls.file(query) if hasattr(cls, "file") else None
        if not path and traversal:
            path = traversal.group(0).strip()
        if not path:
            m = re.search(
                r"\b(?:crea|crear|genera|generar|escribe|escribir)\s+"
                r"(?:el\s+|un\s+|una\s+|el\s+archivo\s+)?"
                r"([^\s\"']+)",
                query,
                re.IGNORECASE,
            )
            if m:
                path = m.group(1).strip()

        return IntentResult(
            intent="file_creation",
            domain="file",
            category="creation",
            confidence=0.92 if (file_keyword or extension) else 0.88,
            entities={
                "path": path or "",
                "task": query,
            },
            signals=[
                s
                for s, flag in (
                    ("file_keyword", bool(file_keyword)),
                    ("extension", bool(extension)),
                    ("path_traversal", bool(traversal)),
                )
                if flag
            ]
            or ["file_creation"],
            original_query=query,
        )

    # =========================================================
    # Module scaffold
    # =========================================================

    @classmethod
    def module_scaffold(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b("
            r"scaffold|esqueleto|"
            r"generar modulo|generar módulo|genera modulo|genera módulo|"
            r"crear modulo|crear módulo|crea modulo|crea módulo"
            r")\b",
            q,
        ):
            return None

        module = None
        m = re.search(
            r"\b("
            r"auth|pos|catalog|catalogo|catálogo|cash|caja|"
            r"payments|pagos|pago|invoicing|facturacion|facturación|"
            r"delivery|reports|reportes"
            r")\b",
            q,
        )
        if m:
            raw = m.group(1)
            aliases = {
                "catalogo": "catalog",
                "catálogo": "catalog",
                "caja": "cash",
                "pagos": "payments",
                "pago": "payments",
                "facturacion": "invoicing",
                "facturación": "invoicing",
                "reportes": "reports",
            }
            module = aliases.get(raw, raw)

        return IntentResult(
            intent="module_scaffold",
            domain="project",
            category="development",
            confidence=0.9,
            entities={
                "module": module or "",
                "task": query,
            },
            signals=["module_scaffold"],
            original_query=query,
        )

    # =========================================================
    # UI scaffold
    # =========================================================

    @classmethod
    def ui_scaffold(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b("
            r"ui shell|ui-shell|scaffold ui|"
            r"generar ui|genera ui|"
            r"login pos|dashboard pos|interfaz pos"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="ui_scaffold",
            domain="frontend",
            category="development",
            confidence=0.9,
            entities={"task": query},
            signals=["ui_scaffold"],
            original_query=query,
        )

    # =========================================================
    # Refactor / debug / testing / spec / planning / docs
    # =========================================================

    @classmethod
    def refactor(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b("
            r"refactor|refactoriza|refactorizar|"
            r"optimiza|optimizar|reestructura|reestructurar|limpia|limpiar"
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
            entities={"task": query},
            signals=["refactor_keyword"],
            original_query=query,
        )

    @classmethod
    def debug(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(error|bug|debug|falla|fallo|problema|excepcion|exception)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="debug",
            domain="code",
            category="maintenance",
            complexity="normal",
            confidence=0.88,
            entities={"task": query},
            signals=["debug_keyword"],
            original_query=query,
        )

    @classmethod
    def testing(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(test|testing|tests|prueba|pruebas|unitario|unitaria|integracion)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="testing",
            domain="code",
            category="testing",
            confidence=0.88,
            entities={"task": query},
            signals=["testing_keyword"],
            original_query=query,
        )

    @classmethod
    def spec(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(spec|specification|especificacion|especificación)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="spec",
            domain="planning",
            category="specification",
            complexity="high",
            confidence=0.92,
            entities={"task": query},
            signals=["spec_keyword"],
            original_query=query,
        )

    @classmethod
    def planning(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(plan|planifica|planificar|roadmap|estrategia)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="planning",
            domain="planning",
            category="strategy",
            complexity="high",
            confidence=0.90,
            entities={"task": query},
            signals=["planning_keyword"],
            original_query=query,
        )

    @classmethod
    def documentation(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(readme|documenta|documentar|documentacion|manual)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="documentation",
            domain="documentation",
            category="generation",
            confidence=0.90,
            entities={"task": query},
            signals=["documentation_keyword"],
            original_query=query,
        )

    @classmethod
    def consolidation(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(consolidate|consolidacion|consolidación|consolidar)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="consolidation",
            domain="memory",
            category="maintenance",
            confidence=0.90,
            entities={"task": query},
            signals=["consolidation_keyword"],
            original_query=query,
        )

    @classmethod
    def rollback(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        if not re.search(
            r"\b(rollback|revertir|revert|deshacer)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="rollback",
            domain="memory",
            category="maintenance",
            confidence=0.90,
            entities={"task": query},
            signals=["rollback_keyword"],
            original_query=query,
        )

    @classmethod
    def analyze_metrics(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:

        analyze = re.search(r"\b(analiza|analizar|analyze)\b", q)
        metrics = re.search(
            r"\b(metricas|métricas|metrics|rendimiento|performance)\b",
            q,
        )
        if not analyze or not metrics:
            return None

        return IntentResult(
            intent="analyze_metrics",
            domain="analytics",
            category="analysis",
            confidence=0.88,
            entities={"task": query},
            signals=["metrics_keyword", "analysis_keyword"],
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
            r"\b(crea|crear|genera|generar|implementa|implementar)\b",
            q,
        )
        code_target = re.search(
            r"\b("
            r"funcion|función|clase|componente|script|endpoint|servicio|"
            r"controller|controlador|middleware|repository|repositorio"
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
            signals=["code_keyword"],
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
            if re.search(rf"\b{re.escape(framework)}\b", q):
                return framework
        return "unknown"

    @staticmethod
    def language(q: str) -> str:
        if re.search(r"\bpython\b", q):
            return "python"
        if re.search(r"\b(php|laravel)\b", q):
            return "php"
        if re.search(r"\b(typescript|ts)\b", q):
            return "typescript"
        if re.search(r"\b(javascript|js)\b", q):
            return "javascript"
        if re.search(r"\b(java|spring)\b", q):
            return "java"
        return "unknown"

    @staticmethod
    def project_name(query: str) -> str:
        patterns = (
            r"(?:llamado|llamada|nombre)\s+([A-Za-z0-9_-]+)",
            r"(?:proyecto)\s+([A-Za-z0-9_-]+)",
        )
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1)
        return "mi_proyecto"

    @staticmethod
    def file(query: str) -> str:
        match = re.search(
            r"([A-Za-z0-9_.\\/-]+\.(?:py|php|js|ts|tsx|jsx|json|md|html|css|yaml|yml|toml))\b",
            query,
            re.IGNORECASE,
        )
        if match:
            return match.group(1)
        return "archivo.txt"
