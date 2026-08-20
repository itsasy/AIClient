from __future__ import annotations

import re
import unicodedata

from core.intent.models import IntentResult


class IntentDetectors:
    """
    Detectores deterministas de intención.

    Principios:
    - Detectores específicos antes que detectores genéricos.
    - La normalización elimina acentos, por lo que las regex no necesitan
      duplicar variantes acentuadas/no acentuadas.
    - Las entidades extraídas deben ser útiles para el planner.
    - No se inventan paths ni contenido de archivos.
    """

    name = "intent_detectors"

    FRAMEWORK_ALIASES = {
        "next": "nextjs",
        "next.js": "nextjs",
        "nextjs": "nextjs",
        "react": "react",
        "reactjs": "react",
        "react.js": "react",
        "vue": "vue",
        "vuejs": "vue",
        "vue.js": "vue",
        "nuxt": "vue",
        "django": "django",
        "laravel": "laravel",
        "nestjs": "nestjs",
        "spring": "spring",
        "fastapi": "fastapi",
        "flutter": "flutter",
    }

    FILE_EXTENSIONS = (
        "py",
        "php",
        "js",
        "ts",
        "tsx",
        "jsx",
        "json",
        "md",
        "txt",
        "html",
        "htm",
        "css",
        "yaml",
        "yml",
        "toml",
        "vue",
    )

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
            cls.module_scaffold,
            cls.ui_scaffold,
            cls.security_audit,
            cls.performance_audit,
            cls.architecture_audit,
            cls.quality_audit,
            cls.project_analysis,
            cls.analyze_metrics,
            cls.testing,
            cls.docker,
            cls.refactor,
            cls.debug,
            cls.file_creation,
            cls.code_generation,
            cls.spec,
            cls.planning,
            cls.documentation,
            cls.consolidation,
            cls.rollback,
            cls.command_execution,
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
            r"laravel|react(?:js)?(?:\.js)?|vue(?:js)?(?:\.js)?|"
            r"django|nestjs|spring|fastapi|"
            r"next(?:\.js)?|flutter"
            r")\b"
        )

        creation_pattern = (
            r"\b("
            r"crear|crea|creando|"
            r"nuevo|nueva|"
            r"generar|genera|"
            r"montar|monta|"
            r"inicializar|inicializa"
            r")\b"
        )

        project_context = re.search(
            r"\b(proyecto|app|aplicacion|aplicativo)\b",
            q,
        )

        if not re.search(framework_pattern, q):
            return None

        if not re.search(creation_pattern, q):
            return None

        if not project_context:
            return None

        framework = cls.framework(q)
        name = cls.project_name(query)

        return IntentResult(
            intent="project_creation",
            domain="project",
            category="creation",
            complexity="high",
            confidence=0.96,
            entities={
                "framework": framework,
                "name": name,
                "task": query,
            },
            signals=[
                "framework_detected",
                "creation_keyword",
                "project_context",
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
        list_dir = re.search(
            r"\b(archivos|ficheros).{0,60}\b(directorio|carpeta|proyecto)\b"
            r"|\b(directorio|carpeta).{0,60}\b(archivos|ficheros)\b",
            q,
        )
        if list_dir:
            return IntentResult(
                intent="project_analysis",
                domain="analysis",
                category="project",
                complexity="normal",
                confidence=0.93,
                entities={"task": query, "mode": "directory_summary"},
                signals=["directory_listing"],
                original_query=query,
            )

        analysis = re.search(
            r"\b("
            r"analiza|analizar|analice|"
            r"revisa|revisar|revise|"
            r"inspecciona|inspeccionar|"
            r"evalua|evaluar|"
            r"resume|resumir|resumen|"
            r"lista|listar|muestra|mostrar"
            r")\b",
            q,
        )
        target = re.search(
            r"\b("
            r"proyecto|repo|repositorio|"
            r"codigo|arquitectura|estructura|"
            r"directorio|carpeta|archivos|"
            r"cwd|workspace"
            r")\b",
            q,
        )
        if not analysis or not target:
            return None

        if re.search(
            r"\b(metricas|metrics|kpi|observabilidad|telemetria)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="project_analysis",
            domain="analysis",
            category="project",
            complexity="high",
            confidence=0.95,
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

        docker_action = re.search(
            r"\b("
            r"build|run|exec|ps|pull|push|"
            r"compose|up|down|restart|stop|start|"
            r"logs|inspect|images|image|container|"
            r"levanta|levantar|"
            r"baja|bajar|"
            r"reinicia|reiniciar|"
            r"detiene|detener|"
            r"arranca|arrancar|"
            r"construye|construir"
            r")\b",
            q,
        )

        docker_file = re.search(
            r"\b(" r"dockerfile|docker-compose|compose\.ya?ml" r")\b",
            q,
        )

        # Docker como mero objeto de análisis no debe tapar otros intents.
        if not docker_action and not docker_file:
            return None

        # "analiza/revisa la seguridad de Docker" debe ir a security_audit.
        if re.search(
            r"\b("
            r"seguridad|vulnerabil|owasp|"
            r"auditoria|audit|"
            r"rendimiento|performance|"
            r"arquitectura|calidad"
            r")\b",
            q,
        ) and re.search(
            r"\b(analiza|analizar|revisa|revisar|audita|auditar)\b",
            q,
        ):
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
                *(["docker_action"] if docker_action else []),
                *(["docker_file"] if docker_file else []),
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
        # Testing tiene prioridad semántica.
        if re.search(
            r"\b("
            r"test|tests|testing|pytest|unittest|"
            r"prueba|pruebas|unitario|unitaria|"
            r"integracion|integracion"
            r")\b",
            q,
        ):
            return None

        if re.search(r"\bdocker\b", q):
            return None

        if not re.search(
            r"\b("
            r"ejecuta|ejecutar|"
            r"run|"
            r"corre|correr|"
            r"lanza|lanzar|"
            r"invoca|invocar"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="command_execution",
            domain="execution",
            category="command",
            complexity="normal",
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
            r"\b(" r"crear|crea|" r"generar|genera|" r"escribe|escribir" r")\b",
            q,
        )

        if not creation:
            return None

        file_keyword = re.search(
            r"\b(archivo|fichero|file)\b",
            q,
        )

        extension = re.search(
            rf"\.({'|'.join(cls.FILE_EXTENSIONS)})\b",
            q,
        )

        traversal = re.search(
            r"(?:\.\./)+[^\s\"']+" r"|(?:^|\s)/[^\s\"']+" r"|(?:^|\s)\.\./[^\s\"']+",
            query,
        )

        explicit_path = cls.file(query)

        if not (file_keyword or extension or traversal or explicit_path):
            return None

        path = explicit_path

        if not path and traversal:
            path = traversal.group(0).strip()

        # No inventar paths aquí.
        # El planner decide defaults si corresponde.
        return IntentResult(
            intent="file_creation",
            domain="file",
            category="creation",
            complexity="normal",
            confidence=(0.94 if explicit_path else 0.92 if file_keyword or extension else 0.88),
            entities={
                "path": path or "",
                "task": query,
                "content": cls.file_content(query),
            },
            signals=[
                signal
                for signal, flag in (
                    (
                        "file_keyword",
                        bool(file_keyword),
                    ),
                    (
                        "extension",
                        bool(extension),
                    ),
                    (
                        "path_traversal",
                        bool(traversal),
                    ),
                    (
                        "explicit_path",
                        bool(explicit_path),
                    ),
                    (
                        "explicit_content",
                        bool(cls.file_content(query)),
                    ),
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
            r"generar\s+modulo|"
            r"genera\s+modulo|"
            r"crear\s+modulo|"
            r"crea\s+modulo"
            r")\b",
            q,
        ):
            return None

        module = None

        match = re.search(
            r"\b("
            r"auth|pos|catalog|catalogo|"
            r"cash|caja|"
            r"payments|pagos|pago|"
            r"invoicing|facturacion|"
            r"delivery|"
            r"reports|reportes"
            r")\b",
            q,
        )

        if match:
            raw = match.group(1)

            aliases = {
                "catalogo": "catalog",
                "caja": "cash",
                "pagos": "payments",
                "pago": "payments",
                "facturacion": "invoicing",
                "reportes": "reports",
            }

            module = aliases.get(
                raw,
                raw,
            )

        return IntentResult(
            intent="module_scaffold",
            domain="project",
            category="development",
            complexity="normal",
            confidence=0.90,
            entities={
                "module": module or "",
                "task": query,
            },
            signals=[
                "module_scaffold",
            ],
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
            r"ui\s+shell|ui-shell|"
            r"scaffold\s+ui|"
            r"generar\s+ui|"
            r"genera\s+ui|"
            r"login\s+pos|"
            r"dashboard\s+pos|"
            r"interfaz\s+pos"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="ui_scaffold",
            domain="frontend",
            category="development",
            complexity="normal",
            confidence=0.90,
            entities={
                "task": query,
            },
            signals=[
                "ui_scaffold",
            ],
            original_query=query,
        )

    # =========================================================
    # Architecture audit
    # =========================================================

    @classmethod
    def architecture_audit(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:
        if not re.search(
            r"\b(auditoria|audit|auditar|audita)\b",
            q,
        ):
            return None

        if not re.search(
            r"\b(arquitectura|architecture|estructura|estructural)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="architecture_audit",
            domain="analysis",
            category="audit",
            complexity="high",
            confidence=0.94,
            entities={
                "task": query,
            },
            signals=[
                "architecture_audit",
            ],
            original_query=query,
        )

    # =========================================================
    # Quality audit
    # =========================================================

    @classmethod
    def quality_audit(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:
        if not re.search(
            r"\b(auditoria|audit|auditar|audita)\b",
            q,
        ):
            return None

        if not re.search(
            r"\b(calidad|quality|codigo|code)\b",
            q,
        ):
            return None

        if re.search(
            r"\b("
            r"seguridad|security|"
            r"performance|rendimiento|"
            r"arquitectura|architecture"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="quality_audit",
            domain="analysis",
            category="audit",
            complexity="high",
            confidence=0.91,
            entities={
                "task": query,
            },
            signals=[
                "quality_audit",
            ],
            original_query=query,
        )

    # =========================================================
    # Security audit
    # =========================================================

    @classmethod
    def security_audit(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:
        if not re.search(
            r"\b(seguridad|security|vulnerabil|owasp)\b",
            q,
        ):
            return None

        if not re.search(
            r"\b("
            r"auditoria|audit|auditar|audita|"
            r"revisa|revisar|"
            r"analiza|analizar|"
            r"evalua|evaluar"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="security_audit",
            domain="analysis",
            category="audit",
            complexity="high",
            confidence=0.94,
            entities={
                "task": query,
            },
            signals=[
                "security_audit",
            ],
            original_query=query,
        )

    # =========================================================
    # Performance audit
    # =========================================================

    @classmethod
    def performance_audit(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:
        if not re.search(
            r"\b(performance|rendimiento|latencia|lento|lenta)\b",
            q,
        ):
            return None

        # Si habla explícitamente de métricas, el detector de métricas
        # debe ganar.
        if re.search(
            r"\b(metricas|metrics|observabilidad|telemetria)\b",
            q,
        ):
            return None

        if not re.search(
            r"\b("
            r"auditoria|audit|auditar|audita|"
            r"analiza|analizar|"
            r"revisa|revisar|"
            r"evalua|evaluar"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="performance_audit",
            domain="analysis",
            category="audit",
            complexity="high",
            confidence=0.92,
            entities={
                "task": query,
            },
            signals=[
                "performance_audit",
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
            r"refactor|refactoriza|refactorizar|"
            r"reestructura|reestructurar|"
            r"limpia|limpiar"
            r")\b",
            q,
        ):
            return None

        if re.search(
            r"\b(" r"documentacion|documentar|" r"readme|" r"logs?|" r"base\s+de\s+datos" r")\b",
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
            r"error|bug|debug|"
            r"falla|fallo|problema|"
            r"excepcion|exception|"
            r"rompe|rompio|"
            r"failing|failed"
            r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="debug",
            domain="code",
            category="maintenance",
            complexity="normal",
            confidence=0.89,
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
        testing_keyword = re.search(
            r"\b("
            r"test|tests|testing|pytest|unittest|"
            r"prueba|pruebas|"
            r"unitario|unitaria|"
            r"integracion"
            r")\b",
            q,
        )

        if not testing_keyword:
            return None

        # No clasificar una simple mención de tests como ejecución.
        action = re.search(
            r"\b("
            r"ejecuta|ejecutar|"
            r"corre|correr|"
            r"lanza|lanzar|"
            r"run|"
            r"corre|"
            r"crea|crear|"
            r"genera|generar|"
            r"escribe|escribir|"
            r"haz|hacer|"
            r"pasa|pasar|"
            r"verifica|verificar|"
            r"corre"
            r")\b",
            q,
        )

        test_file = re.search(
            r"\b(" r"test_.*\.py|" r".*_test\.py|" r"tests?/|" r"spec/" r")\b",
            q,
        )

        if not action and not test_file:
            return None

        return IntentResult(
            intent="testing",
            domain="code",
            category="testing",
            complexity="normal",
            confidence=0.91,
            entities={
                "task": query,
            },
            signals=[
                "testing_keyword",
                *(["testing_action"] if action else []),
                *(["test_file"] if test_file else []),
            ],
            original_query=query,
        )

    # =========================================================
    # Spec
    # =========================================================

    @classmethod
    def spec(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:
        if not re.search(
            r"\b(" r"spec|specification|" r"especificacion" r")\b",
            q,
        ):
            return None

        # "donde esta la spec" no significa crear una spec.
        creation = re.search(
            r"\b("
            r"crear|crea|"
            r"generar|genera|"
            r"escribir|escribe|"
            r"definir|define|"
            r"documentar|documenta|"
            r"preparar|prepara|"
            r"hacer|haz"
            r")\b",
            q,
        )

        if not creation:
            return None

        return IntentResult(
            intent="spec",
            domain="planning",
            category="specification",
            complexity="high",
            confidence=0.93,
            entities={
                "task": query,
            },
            signals=[
                "spec_keyword",
                "spec_creation_action",
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
            r"\b(" r"plan|planifica|planificar|" r"roadmap|estrategia" r")\b",
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
            r"\b(" r"readme|" r"documenta|documentar|" r"documentacion|" r"manual" r")\b",
            q,
        ):
            return None

        creation = re.search(
            r"\b("
            r"crear|crea|"
            r"generar|genera|"
            r"escribir|escribe|"
            r"documenta|documentar|"
            r"actualiza|actualizar|"
            r"redacta|redactar"
            r")\b",
            q,
        )

        if not creation:
            return None

        return IntentResult(
            intent="documentation",
            domain="documentation",
            category="generation",
            complexity="normal",
            confidence=0.91,
            entities={
                "task": query,
            },
            signals=[
                "documentation_keyword",
                "documentation_action",
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
            r"\b(" r"consolidate|" r"consolidacion|" r"consolidar" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="consolidation",
            domain="memory",
            category="maintenance",
            complexity="normal",
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
            r"\b(" r"rollback|revertir|revert|deshacer" r")\b",
            q,
        ):
            return None

        return IntentResult(
            intent="rollback",
            domain="memory",
            category="maintenance",
            complexity="normal",
            confidence=0.91,
            entities={
                "task": query,
            },
            signals=[
                "rollback_keyword",
            ],
            original_query=query,
        )

    # =========================================================
    # Analyze metrics
    # =========================================================

    @classmethod
    def analyze_metrics(
        cls,
        query: str,
        q: str,
    ) -> IntentResult | None:
        if not re.search(
            r"\b(analiza|analizar|analyze|evalua|evaluar|revisa|revisar)\b",
            q,
        ):
            return None

        if not re.search(
            r"\b("
            r"metricas|metrics|kpi|"
            r"observabilidad|telemetria|"
            r"rendimiento|performance|latencia"
            r")\b",
            q,
        ):
            return None

        if re.search(
            r"\b(proyecto|repo|repositorio|arquitectura|directorio|"
            r"archivos|codigo|estructura)\b",
            q,
        ) and not re.search(
            r"\b(metricas|metrics|kpi|observabilidad|telemetria)\b",
            q,
        ):
            return None

        return IntentResult(
            intent="analyze_metrics",
            domain="analytics",
            category="analysis",
            complexity="normal",
            confidence=0.90,
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
            r"\b("
            r"crea|crear|"
            r"genera|generar|"
            r"implementa|implementar|"
            r"escribe|escribir"
            r")\b",
            q,
        )

        code_target = re.search(
            r"\b("
            r"funcion|"
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
            complexity="normal",
            confidence=0.87,
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

    @classmethod
    def framework(
        cls,
        q: str,
    ) -> str:
        patterns = (
            ("nextjs", r"\bnext(?:\.js|js)?\b"),
            ("react", r"\breact(?:\.js|js)?\b"),
            ("vue", r"\bvue(?:\.js|js)?\b"),
            ("laravel", r"\blaravel\b"),
            ("django", r"\bdjango\b"),
            ("nestjs", r"\bnestjs\b"),
            ("spring", r"\bspring\b"),
            ("fastapi", r"\bfastapi\b"),
            ("flutter", r"\bflutter\b"),
        )

        for framework, pattern in patterns:
            if re.search(pattern, q):
                return framework

        return "unknown"

    @staticmethod
    def language(
        q: str,
    ) -> str:
        if re.search(r"\bpython\b", q):
            return "python"

        if re.search(
            r"\b(php|laravel)\b",
            q,
        ):
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
            r"(?:llamado|llamada|nombre|named|called)\s+" r"([A-Za-z0-9_-]+)",
            r"\bproyecto\s+([A-Za-z0-9_-]+)",
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

    @classmethod
    def file(
        cls,
        query: str,
    ) -> str:
        extensions = "|".join(re.escape(extension) for extension in cls.FILE_EXTENSIONS)

        # Prioridad: path entre comillas.
        quoted = re.search(
            rf"""['"]([A-Za-z0-9_.\\/-]+\.({extensions}))['"]""",
            query,
            re.IGNORECASE,
        )

        if quoted:
            return quoted.group(1)

        # Path explícito.
        explicit = re.search(
            rf"\b([A-Za-z0-9_.\\/-]+\.({extensions}))\b",
            query,
            re.IGNORECASE,
        )

        if explicit:
            candidate = explicit.group(1)

            if not re.search(
                r"https?://|www\.",
                candidate,
                re.IGNORECASE,
            ):
                return candidate

        return ""

    @staticmethod
    def file_content(
        query: str,
    ) -> str:
        if not isinstance(query, str):
            return ""

        patterns = (
            r"con\s+el\s+contenido\s+(.+)$",
            r"con\s+contenido\s+(.+)$",
            r"que\s+contenga\s+(.+)$",
            r"conteniendo\s+(.+)$",
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                query,
                re.IGNORECASE,
            )

            if not match:
                continue

            content = match.group(1).strip()

            if len(content) >= 2 and content[0] in {"'", '"'} and content[-1] == content[0]:
                content = content[1:-1]

            return content

        return ""
