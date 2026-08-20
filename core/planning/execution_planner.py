from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from core.execution_plan import ExecutionPlan
from core.intent import IntentResult
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Constructor declarativo de ExecutionPlans.

    Decide CÓMO debe ejecutarse una intención.
    Nunca ejecuta Agents ni Skills.

    Principios:
    - El IntentResult aporta la interpretación semántica.
    - El planner decide la estrategia de ejecución.
    - depends_on expresa orden/dependencia de ejecución.
    - metadata "consumes" / "produces" documenta el flujo de datos.
    - Nunca se confía ciegamente en nombres generados por el LLM.
    """

    name = "execution_planner"

    SUPPORTED_UNIT_TYPES = {
        "agent",
        "skill",
    }

    KNOWN_AGENTS = {
        "architect",
        "coder",
        "multi_turn",
        "task_agent",
    }

    KNOWN_SKILLS = {
        "analyze_project",
        "architecture_audit",
        "quality_audit",
        "security_audit",
        "performance_audit",
        "write_file",
        "create_project",
        "scaffold_module",
        "scaffold_ui_shell",
        "sandbox",
        "shell",
        "readme",
        "ingest",
        "scrape_job",
        "scrape_integration",
    }

    FRAMEWORK_ALIASES = {
        "next": "nextjs",
        "next.js": "nextjs",
        "nextjs": "nextjs",
        "reactjs": "react",
        "react.js": "react",
        "react": "react",
        "vuejs": "vue",
        "vue.js": "vue",
        "vue": "vue",
        "nuxt": "vue",
        "django": "django",
        "laravel": "laravel",
        "nestjs": "nestjs",
        "spring": "spring",
        "fastapi": "fastapi",
        "flutter": "flutter",
    }

    FILE_EXTENSIONS = frozenset(
        {
            "html",
            "htm",
            "css",
            "js",
            "ts",
            "tsx",
            "jsx",
            "py",
            "json",
            "md",
            "txt",
            "vue",
            "php",
            "yaml",
            "yml",
            "toml",
        }
    )

    BARE_EXTENSIONS = frozenset(
        {f".{extension}" for extension in FILE_EXTENSIONS} | FILE_EXTENSIONS
    )

    INVALID_PATH_TOKENS = frozenset(
        {
            "archivo",
            "fichero",
            "file",
            "page",
            "pagina",
            "landing",
            "script",
            "codigo",
            "code",
            "un",
            "una",
            "el",
            "la",
            "de",
            "con",
            "contenido",
        }
    )

    # =========================================================
    # Public API
    # =========================================================

    @classmethod
    def create(
        cls,
        task: str,
        intent: IntentResult | dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        if not task or not task.strip():
            raise ValueError("ExecutionPlanner requiere una tarea.")

        task = task.strip()

        intent_result = cls._normalize_intent(intent)

        intent_name = cls._normalize(intent_result.intent or "conversation")
        domain = cls._normalize(intent_result.domain or "general")
        complexity = cls._normalize(intent_result.complexity or "normal")

        plan = ExecutionPlan(original_task=task)

        plan.intent = intent_name
        plan.intent_category = domain
        plan.objective = task

        plan.params.update(intent_result.entities or {})

        plan.metadata.update(
            {
                "planner": cls.name,
                "intent": intent_name,
                "domain": domain,
                "complexity": complexity,
                "confidence": intent_result.confidence,
            }
        )

        if complexity in {
            "high",
            "complex",
            "very_high",
        }:
            plan.execution_mode = "multi_step"
        else:
            plan.execution_mode = "single"

        planner_method = getattr(
            cls,
            f"_plan_{intent_name}",
            None,
        )

        if planner_method is None:
            logger.warning(
                "Intent no soportado=%s → fallback conversation",
                intent_name,
            )
            planner_method = cls._plan_conversation

        planner_method(
            plan,
            task,
            intent_result,
        )

        errors = plan.validate()

        if errors:
            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        plan.mark_planned()

        logger.info(
            "ExecutionPlan creado | intent=%s | mode=%s | steps=%d | unit=%s:%s",
            intent_name,
            plan.execution_mode,
            len(plan.steps),
            plan.execution_unit_type,
            plan.execution_unit,
        )

        for index, step in enumerate(
            plan.steps,
            start=1,
        ):
            logger.info(
                "Plan step=%d | id=%s | unit=%s:%s | depends_on=%s",
                index,
                step.id,
                step.unit_type,
                step.unit_name,
                step.depends_on,
            )

        return plan

    # =========================================================
    # Intent normalization
    # =========================================================

    @staticmethod
    def _normalize_intent(
        intent: IntentResult | dict[str, Any] | None,
    ) -> IntentResult:
        if isinstance(
            intent,
            IntentResult,
        ):
            return intent

        if isinstance(
            intent,
            dict,
        ):
            return IntentResult(
                intent=intent.get(
                    "intent",
                    "conversation",
                ),
                domain=intent.get(
                    "domain",
                    "general",
                ),
                category=intent.get(
                    "category",
                    "general",
                ),
                complexity=intent.get(
                    "complexity",
                    "normal",
                ),
                confidence=float(
                    intent.get(
                        "confidence",
                        0.0,
                    )
                    or 0.0
                ),
                entities=dict(intent.get("entities") or {}),
                signals=list(intent.get("signals") or []),
                original_query=str(intent.get("original_query") or intent.get("query") or ""),
                metadata=dict(intent.get("metadata") or {}),
            )

        return IntentResult(
            intent="conversation",
            domain="general",
            category="general",
            complexity="low",
            confidence=0.0,
            entities={},
            signals=[],
            original_query="",
            metadata={},
        )

    # =========================================================
    # Helpers
    # =========================================================

    @staticmethod
    def _normalize(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return str(value).strip().lower()

    @classmethod
    def _entity(
        cls,
        intent: IntentResult,
        key: str,
        default: Any = None,
    ) -> Any:
        entities = (
            getattr(
                intent,
                "entities",
                None,
            )
            or {}
        )

        value = entities.get(key)

        if value is None:
            return default

        return value

    @classmethod
    def _normalize_framework(
        cls,
        value: Any,
    ) -> str:
        raw = str(value or "").strip().lower()

        return cls.FRAMEWORK_ALIASES.get(
            raw,
            raw or "unknown",
        )

    @staticmethod
    def _looks_like_url(
        value: str,
    ) -> bool:
        return bool(
            re.search(
                r"https?://|www\.|" r"\.com(?:/|$|\s)|" r"\.ar(?:/|$|\s)",
                value,
                re.IGNORECASE,
            )
        )

    @classmethod
    def _sanitize_output_path(
        cls,
        path: str,
    ) -> str:
        """
        Sanitiza exclusivamente.

        No inventa nombres por defecto.
        """
        p = (path or "").strip().strip("'\"")

        if not p:
            return ""

        if cls._looks_like_url(p):
            return ""

        normalized = p.lower().lstrip("./")

        if normalized in cls.BARE_EXTENSIONS:
            return ""

        if normalized in cls.INVALID_PATH_TOKENS:
            return ""

        p = re.sub(
            r"\s+$",
            "",
            p,
        )

        return p

    @classmethod
    def _default_output_path(
        cls,
        task: str,
    ) -> str:
        """
        Decide un path por defecto cuando el usuario no especificó uno.
        """
        task_l = (task or "").lower()

        wants_landing = bool(
            re.search(
                r"\b(" r"landing|" r"pagina\s+web|" r"página\s+web" r")\b",
                task_l,
            )
            or re.search(
                r"\bhtml\b",
                task_l,
            )
        )

        if wants_landing:
            return "landing.html"

        if re.search(
            r"\bpython\b|\.py\b",
            task_l,
        ):
            return "main.py"

        return "archivo.txt"

    @classmethod
    def _extract_file_path(
        cls,
        task: str,
    ) -> str:
        if (
            not isinstance(
                task,
                str,
            )
            or not task.strip()
        ):
            return ""

        explicit = re.search(
            r"""path\s*[:=]\s*['"]([^'"]+)['"]""",
            task,
            re.IGNORECASE,
        )

        if explicit:
            candidate = cls._sanitize_output_path(explicit.group(1))

            if candidate:
                return candidate

        extensions = "|".join(
            sorted(
                (re.escape(extension) for extension in cls.FILE_EXTENSIONS),
                key=len,
                reverse=True,
            )
        )

        quoted = re.search(
            rf"""['"]([A-Za-z0-9_.\\/-]+\.({extensions}))['"]""",
            task,
            re.IGNORECASE,
        )

        if quoted:
            candidate = cls._sanitize_output_path(quoted.group(1))

            if candidate:
                return candidate

        plain = re.search(
            rf"\b([A-Za-z0-9_.\\/-]+\.({extensions}))\b",
            task,
            re.IGNORECASE,
        )

        if plain:
            candidate = cls._sanitize_output_path(plain.group(1))

            if candidate:
                return candidate

        patterns = (
            r"\bel\s+archivo\s+[\"']([^\"']+)[\"']",
            r"\barchivo\s+[\"']([^\"']+)[\"']",
            r"\bel\s+archivo\s+([^\s\"']+)",
            r"\barchivo\s+([^\s\"']+)",
            r"\b(?:crea|crear|genera|generar|"
            r"escribe|escribir)\s+"
            r"(?:un\s+|una\s+)?"
            r"(?:archivo\s+)?"
            r"(?:llamado\s+|llamada\s+|"
            r"de\s+nombre\s+)?"
            r"([^\s\"']+\.[a-zA-Z0-9]+)",
        )

        for pattern in patterns:
            match = re.search(
                pattern,
                task,
                re.IGNORECASE,
            )

            if not match:
                continue

            candidate = cls._sanitize_output_path(match.group(1))

            if candidate:
                return candidate

        return ""

    @staticmethod
    def _extract_file_content(
        task: str,
    ) -> str:
        if not isinstance(
            task,
            str,
        ):
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
                task,
                re.IGNORECASE,
            )

            if not match:
                continue

            content = match.group(1).strip()

            if len(content) >= 2 and content[0] in {"'", '"'} and content[-1] == content[0]:
                content = content[1:-1]

            return content

        return ""

    @classmethod
    def _set_execution_unit(
        cls,
        plan: ExecutionPlan,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        unit_type = cls._normalize(unit_type)

        unit_name = str(unit_name or "").strip()

        if unit_type not in cls.SUPPORTED_UNIT_TYPES:
            raise ValueError(
                f"Tipo de unidad inválido: {unit_type!r}. " "Debe ser 'agent' o 'skill'."
            )

        if not unit_name:
            raise ValueError("unit_name no puede estar vacío.")

        if params is None:
            params = {}

        if not isinstance(
            params,
            dict,
        ):
            raise TypeError("params debe ser un diccionario.")

        if plan.is_single():
            plan.set_execution_unit(
                unit_type=unit_type,
                unit_name=unit_name,
                params=params,
            )
            return

        plan.add_step(
            description=(f"Ejecutar {unit_type}: " f"{unit_name}"),
            unit_type=unit_type,
            unit_name=unit_name,
            params=params,
            expected_output=(f"Resultado de {unit_type}: " f"{unit_name}"),
        )

    @staticmethod
    def _clear_context_requirements(
        plan: ExecutionPlan,
    ) -> None:
        for key in plan.context_requirements:
            plan.context_requirements[key] = False

    @staticmethod
    def _add_dependency(
        step: Any,
        dependency: Any,
    ) -> None:
        if dependency.id not in step.depends_on:
            step.depends_on.append(dependency.id)

    @staticmethod
    def _mark_data_flow(
        step: Any,
        *,
        consumes: str | None = None,
        consumes_from: Any | None = None,
        produces: str | None = None,
    ) -> None:
        """
        Documenta el flujo de datos sin asumir una API adicional
        de ExecutionPlan.

        La dependencia real sigue estando expresada por depends_on.
        """
        metadata = getattr(
            step,
            "metadata",
            None,
        )

        if metadata is None:
            return

        if produces:
            metadata["produces"] = produces

        if consumes:
            metadata["consumes"] = consumes

        if consumes_from is not None:
            metadata["consumes_from_step"] = consumes_from.id

    # =========================================================
    # Planning strategies
    # =========================================================

    @staticmethod
    def _plan_conversation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = task
        plan.execution_mode = "single"

        ExecutionPlanner._clear_context_requirements(plan)

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "multi_turn",
            {
                "task": task,
            },
        )

    @classmethod
    def _plan_file_creation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Crear archivo"
        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = False
        plan.context_requirements["standards"] = True
        plan.context_requirements["gentleman"] = False

        plan.governance["allow_write"] = True

        path = cls._extract_file_path(task)

        entity_path = str(cls._entity(intent, "path", "") or "").strip()

        if entity_path:
            sanitized_entity_path = cls._sanitize_output_path(entity_path)
            if sanitized_entity_path:
                path = sanitized_entity_path

        if not path:
            path = cls._default_output_path(task)

        path = cls._sanitize_output_path(path) or cls._default_output_path(task)

        content = cls._extract_file_content(task)
        if not content:
            entity_content = cls._entity(intent, "content", "")
            if isinstance(entity_content, str):
                content = entity_content.strip()

        # -----------------------------------------------------
        # Contenido explícito → write_file directo
        # -----------------------------------------------------
        if content:
            plan.execution_mode = "single"
            cls._set_execution_unit(
                plan,
                "skill",
                "write_file",
                {
                    "path": path,
                    "content": content,
                },
            )
            logger.info(
                "File creation (explicit content) | path=%s | content_length=%d",
                path,
                len(content),
            )
            return

        # -----------------------------------------------------
        # Multi-phase: referencia URL/landing → scrape|analyze → coder → write
        # -----------------------------------------------------
        if cls._is_multi_phase_landing_request(task):
            url_match = re.search(r"https?://[^\s]+", task)
            url = url_match.group(0).rstrip(".,);]") if url_match else ""

            if url:
                analyze_step = plan.add_step(
                    description="Obtener y resumir la página de referencia",
                    unit_type="skill",
                    unit_name="scrape_job",
                    params={
                        "url": url,
                        "task": task,
                    },
                    expected_output="Evidencia textual/estructura de la URL",
                    metadata={
                        "stage": "scrape",
                        "produces": "landing_analysis",
                    },
                    timeout=120,
                )
                plan.governance["allow_network"] = True
            else:
                analyze_step = plan.add_step(
                    description="Analizar la landing de referencia",
                    unit_type="agent",
                    unit_name="task_agent",
                    params={
                        "task": (
                            "Analiza la referencia indicada en la tarea. "
                            "Extrae secciones, copy, conversión y estilo. "
                            "Solo análisis, sin código."
                        ),
                    },
                    expected_output="Análisis estructurado de la referencia",
                    metadata={
                        "stage": "analysis",
                        "produces": "landing_analysis",
                    },
                    timeout=180,
                )

            coder_step = plan.add_step(
                description=f"Generar HTML completo para {path}",
                unit_type="agent",
                unit_name="coder",
                params={
                    "task": task,
                    "path": path,
                    "landing": True,
                },
                expected_output="code_artifact con HTML completo",
                metadata={"stage": "generation"},
                timeout=180,
            )
            cls._add_dependency(coder_step, analyze_step)
            cls._mark_data_flow(
                coder_step,
                consumes="landing_analysis",
                consumes_from=analyze_step,
                produces="code_artifact",
            )

            write_step = plan.add_step(
                description=f"Escribir archivo {path}",
                unit_type="skill",
                unit_name="write_file",
                params={"path": path},
                expected_output="Archivo creado en disco",
                metadata={"stage": "materialization"},
                timeout=60,
            )
            cls._add_dependency(write_step, coder_step)
            cls._mark_data_flow(
                write_step,
                consumes="code_artifact",
                consumes_from=coder_step,
            )

            logger.info(
                "File creation (multi-phase: %s→coder→write_file) | path=%s | url=%s",
                "scrape" if url else "analyze",
                path,
                bool(url),
            )
            return

        # -----------------------------------------------------
        # Simple: coder → write_file
        # -----------------------------------------------------
        coder_step = plan.add_step(
            description=f"Generar contenido para {path}",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
                "path": path,
            },
            expected_output="code_artifact con path y content",
            metadata={"stage": "generation"},
            timeout=180,
        )
        cls._mark_data_flow(
            coder_step,
            produces="code_artifact",
        )

        write_step = plan.add_step(
            description=f"Escribir archivo {path}",
            unit_type="skill",
            unit_name="write_file",
            params={"path": path},
            expected_output="Archivo creado en disco",
            metadata={"stage": "materialization"},
            timeout=60,
        )
        cls._add_dependency(write_step, coder_step)
        cls._mark_data_flow(
            write_step,
            consumes="code_artifact",
            consumes_from=coder_step,
        )

        logger.info(
            "File creation (coder→write_file) | path=%s",
            path,
        )

    @staticmethod
    def _plan_module_scaffold(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        module = (
            str(
                ExecutionPlanner._entity(
                    intent,
                    "module",
                    "",
                )
                or ""
            )
            .strip()
            .lower()
        )

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

        module = aliases.get(
            module,
            module,
        )

        plan.objective = f"Scaffold módulo " f"{module or '(sin nombre)'}"

        plan.execution_mode = "single"

        plan.context_requirements["project"] = False
        plan.context_requirements["engram"] = False

        plan.governance["allow_write"] = True

        plan.metadata["module"] = module

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "scaffold_module",
            {
                "module": module,
            },
        )

    @staticmethod
    def _plan_ui_scaffold(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Scaffold UI shell POS"
        plan.execution_mode = "single"

        plan.context_requirements["project"] = False

        plan.governance["allow_write"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "scaffold_ui_shell",
            {},
        )

    @staticmethod
    def _plan_code_generation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Generar código"

        plan.context_requirements["gentleman"] = True
        plan.context_requirements["standards"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "coder",
            {
                "task": task,
                "language": ExecutionPlanner._entity(
                    intent,
                    "language",
                    "unknown",
                ),
            },
        )

    @classmethod
    def _plan_project_analysis(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        """
        Analiza un proyecto/directorio y posteriormente
        genera una interpretación ejecutiva de la evidencia.

        También cubre solicitudes como:
        "Realiza un resumen conciso de los archivos
        que ves en este directorio."
        """
        plan.objective = "Analizar y resumir el proyecto o directorio"

        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        inspect = plan.add_step(
            description=("Inspeccionar estructura, archivos " "y componentes del proyecto"),
            unit_type="skill",
            unit_name="analyze_project",
            params={
                "path": ".",
                "task": task,
                "prefer_target": False,
            },
            expected_output=("Snapshot estructurado del proyecto."),
            metadata={
                "stage": "inspection",
            },
        )

        cls._mark_data_flow(
            inspect,
            produces="project_analysis",
        )

        architect = plan.add_step(
            description=("Interpretar la evidencia y generar " "un resumen ejecutivo"),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
            expected_output=("Resumen ejecutivo / análisis " "del proyecto."),
            metadata={
                "stage": "architecture_analysis",
            },
            timeout=300,
        )

        cls._add_dependency(
            architect,
            inspect,
        )

        cls._mark_data_flow(
            architect,
            consumes="project_analysis",
            consumes_from=inspect,
        )

    @classmethod
    def _plan_architecture_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Auditar arquitectura del proyecto"

        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True

        evidence = plan.add_step(
            description=("Recolectar evidencia estructural " "del proyecto"),
            unit_type="skill",
            unit_name="architecture_audit",
            params={
                "task": task,
            },
            expected_output=("architecture_evidence"),
            metadata={
                "stage": "evidence",
            },
        )

        cls._mark_data_flow(
            evidence,
            produces="architecture_evidence",
        )

        analysis = plan.add_step(
            description=("Evaluar arquitectura a partir " "de la evidencia"),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
            expected_output=("Informe arquitectónico ejecutivo."),
            metadata={
                "stage": "analysis",
            },
        )

        cls._add_dependency(
            analysis,
            evidence,
        )

        cls._mark_data_flow(
            analysis,
            consumes="architecture_evidence",
            consumes_from=evidence,
        )

    @classmethod
    def _plan_quality_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Auditar calidad del código"

        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True

        evidence = plan.add_step(
            description=("Recolectar evidencia de calidad"),
            unit_type="skill",
            unit_name="quality_audit",
            params={
                "task": task,
            },
            expected_output="quality_evidence",
            metadata={
                "stage": "evidence",
            },
        )

        cls._mark_data_flow(
            evidence,
            produces="quality_evidence",
        )

        analysis = plan.add_step(
            description=("Evaluar calidad a partir " "de la evidencia"),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
                "mode": "quality",
            },
            expected_output=("Informe de calidad."),
            metadata={
                "stage": "analysis",
            },
        )

        cls._add_dependency(
            analysis,
            evidence,
        )

        cls._mark_data_flow(
            analysis,
            consumes="quality_evidence",
            consumes_from=evidence,
        )

    @classmethod
    def _plan_security_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Auditar seguridad del proyecto"

        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True

        evidence = plan.add_step(
            description=("Recolectar evidencia de seguridad"),
            unit_type="skill",
            unit_name="security_audit",
            params={
                "task": task,
            },
            expected_output="security_evidence",
            metadata={
                "stage": "evidence",
            },
        )

        cls._mark_data_flow(
            evidence,
            produces="security_evidence",
        )

        analysis = plan.add_step(
            description=("Evaluar riesgos de seguridad"),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
                "mode": "security",
            },
            expected_output=("Informe de seguridad."),
            metadata={
                "stage": "analysis",
            },
        )

        cls._add_dependency(
            analysis,
            evidence,
        )

        cls._mark_data_flow(
            analysis,
            consumes="security_evidence",
            consumes_from=evidence,
        )

    @classmethod
    def _plan_performance_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Auditar rendimiento del proyecto"

        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = True

        evidence = plan.add_step(
            description=("Recolectar evidencia " "de rendimiento"),
            unit_type="skill",
            unit_name="performance_audit",
            params={
                "task": task,
            },
            expected_output=("performance_evidence"),
            metadata={
                "stage": "evidence",
            },
        )

        cls._mark_data_flow(
            evidence,
            produces="performance_evidence",
        )

        analysis = plan.add_step(
            description=("Evaluar rendimiento a partir " "de la evidencia"),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
                "mode": "performance",
            },
            expected_output=("Informe de rendimiento."),
            metadata={
                "stage": "analysis",
            },
        )

        cls._add_dependency(
            analysis,
            evidence,
        )

        cls._mark_data_flow(
            analysis,
            consumes="performance_evidence",
            consumes_from=evidence,
        )

    @classmethod
    def _plan_project_creation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Crear un nuevo proyecto " "de software"

        plan.execution_mode = "multi_step"

        framework_raw = cls._entity(
            intent,
            "framework",
            "unknown",
        )

        if not framework_raw or framework_raw == "unknown":
            lower = task.lower()

            framework_patterns = (
                ("next.js", "nextjs"),
                ("nextjs", "nextjs"),
                ("next", "nextjs"),
                ("react.js", "react"),
                ("reactjs", "react"),
                ("react", "react"),
                ("vue.js", "vue"),
                ("vuejs", "vue"),
                ("vue", "vue"),
                ("laravel", "laravel"),
                ("django", "django"),
                ("nestjs", "nestjs"),
                ("spring", "spring"),
                ("fastapi", "fastapi"),
                ("flutter", "flutter"),
            )

            for token, normalized in framework_patterns:
                if re.search(
                    rf"\b{re.escape(token)}\b",
                    lower,
                ):
                    framework_raw = normalized
                    break

        framework = cls._normalize_framework(framework_raw)

        name = str(
            cls._entity(
                intent,
                "name",
                "mi_proyecto",
            )
            or "mi_proyecto"
        ).strip()

        if not name or name == "mi_proyecto":
            match = re.search(
                r"(?:llamado|llamada|" r"called|named|" r"nombre)\s+" r"([a-zA-Z0-9_-]+)",
                task,
                re.IGNORECASE,
            )

            if match:
                name = match.group(1)

        plan.context_requirements["project"] = False
        plan.context_requirements["gentleman"] = True

        plan.governance["allow_write"] = True

        plan.params["framework"] = framework
        plan.params["name"] = name

        analyze = plan.add_step(
            description=(f"Analizar requisitos para " f"proyecto {framework}"),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
                "framework": framework,
                "name": name,
            },
            expected_output=("Decisiones arquitectónicas y " "requisitos estructurados."),
            metadata={
                "stage": "requirements",
                "produces": "project_requirements",
            },
        )

        generate = plan.add_step(
            description=(f"Generar estructura inicial " f"para {framework}"),
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
                "framework": framework,
                "project_name": name,
            },
            expected_output=("Estructura inicial y código base " "del proyecto."),
            metadata={
                "stage": "generation",
                "produces": "project_artifact",
            },
        )

        cls._add_dependency(
            generate,
            analyze,
        )

        cls._mark_data_flow(
            generate,
            consumes="project_requirements",
            consumes_from=analyze,
        )

        create = plan.add_step(
            description=(f"Materializar proyecto {name}"),
            unit_type="skill",
            unit_name="create_project",
            params={
                "framework": framework,
                "name": name,
                "task": task,
            },
            expected_output=("Proyecto creado en disco."),
            metadata={
                "stage": "materialization",
            },
        )

        cls._add_dependency(
            create,
            generate,
        )

        cls._mark_data_flow(
            create,
            consumes="project_artifact",
            consumes_from=generate,
        )

    @classmethod
    def _plan_debug(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Analizar y diagnosticar " "problema técnico"

        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = True
        plan.context_requirements["engram"] = True

        analyze = plan.add_step(
            description="Analizar problema",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
            expected_output=("Diagnóstico técnico del problema."),
            metadata={
                "stage": "diagnosis",
                "produces": "diagnostic",
            },
        )

        validate = plan.add_step(
            description="Ejecutar validaciones",
            unit_type="skill",
            unit_name="sandbox",
            params={
                "task": task,
            },
            expected_output=("Resultado de validaciones."),
            metadata={
                "stage": "validation",
            },
        )

        cls._add_dependency(
            validate,
            analyze,
        )

        cls._mark_data_flow(
            validate,
            consumes="diagnostic",
            consumes_from=analyze,
        )

    @classmethod
    def _plan_refactor(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Analizar y proponer " "refactorización de código"

        plan.execution_mode = "multi_step"

        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True

        plan.governance["allow_write"] = False

        analyze = plan.add_step(
            description=("Analizar arquitectura actual"),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
            expected_output=("Análisis arquitectónico y " "estrategia de refactorización."),
            metadata={
                "stage": "analysis",
                "produces": "refactor_strategy",
            },
        )

        modify = plan.add_step(
            description=("Generar cambios de código " "propuestos"),
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
            expected_output=("code_artifact con cambios propuestos."),
            metadata={
                "stage": "proposal",
            },
        )

        cls._add_dependency(
            modify,
            analyze,
        )

        cls._mark_data_flow(
            modify,
            consumes="refactor_strategy",
            consumes_from=analyze,
            produces="code_artifact",
        )

    @staticmethod
    def _plan_documentation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Crear documentación"

        plan.execution_mode = "single"

        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "task_agent",
            {
                "task": task,
                "mode": "documentation",
            },
        )

    @staticmethod
    def _plan_command_execution(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Ejecutar comando"

        plan.execution_mode = "single"

        plan.context_requirements["project"] = True

        plan.governance["allow_shell"] = True

        command = task.strip()

        command = re.sub(
            r"^(?:"
            r"ejecuta|"
            r"ejecutar|"
            r"run|"
            r"corre|"
            r"correr|"
            r"lanza|"
            r"lanzar|"
            r"please\s+run"
            r")\s+",
            "",
            command,
            flags=re.IGNORECASE,
        ).strip()

        if not command:
            command = task.strip()

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "shell",
            {
                "command": command,
                "task": task,
            },
        )

    @staticmethod
    def _plan_docker(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Operación Docker"

        plan.execution_mode = "single"

        plan.context_requirements["project"] = True

        plan.governance["allow_shell"] = True
        plan.governance["allow_network"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "sandbox",
            {
                "task": task,
            },
        )

    @staticmethod
    def _plan_spec(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Crear especificación (Spec)"

        plan.execution_mode = "multi_step"

        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        plan.governance["allow_write"] = True

        try:
            from core.specs.paths import spec_path_for

            path = spec_path_for(task)

        except Exception:
            path = ".specs/spec.md"

        spec_step = plan.add_step(
            description=("Generar especificación detallada " "a partir de la tarea"),
            unit_type="agent",
            unit_name="task_agent",
            params={
                "task": task,
                "mode": "spec",
                "path": path,
            },
            expected_output=("Especificación estructurada."),
            metadata={
                "stage": "spec_generation",
                "produces": "spec_artifact",
            },
        )

        write_spec = plan.add_step(
            description=("Guardar especificación en disco"),
            unit_type="skill",
            unit_name="write_file",
            params={
                "path": path,
            },
            expected_output=("Archivo de especificación creado."),
            metadata={
                "stage": "materialization",
            },
        )

        ExecutionPlanner._add_dependency(
            write_spec,
            spec_step,
        )

        ExecutionPlanner._mark_data_flow(
            write_spec,
            consumes="spec_artifact",
            consumes_from=spec_step,
        )

    @classmethod
    def _plan_planning(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Generar un plan de ejecución"

        plan.execution_mode = "multi_step"

        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        cls._generate_steps_with_llm(
            plan,
            task,
            intent,
        )

        if not plan.steps:
            plan.execution_mode = "single"

            cls._set_execution_unit(
                plan,
                "agent",
                "task_agent",
                {
                    "task": task,
                    "mode": "planning",
                },
            )

    @staticmethod
    def _plan_testing(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Ejecutar pruebas del proyecto"

        plan.execution_mode = "single"

        plan.context_requirements["project"] = False

        plan.governance["allow_shell"] = True

        cmd = "pytest -q"

        lower = task.lower()

        if "pytest" in lower:
            match = re.search(
                r"\bpytest\b[^\n\r]*",
                task,
                re.IGNORECASE,
            )

            if match:
                cmd = match.group(0).strip()

        elif "unittest" in lower:
            cmd = "python -m unittest"

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "shell",
            {
                "command": cmd,
                "task": task,
            },
        )

    @staticmethod
    def _plan_consolidation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Consolidar conocimiento / memoria"

        plan.execution_mode = "single"

        plan.context_requirements["engram"] = True

        plan.governance["allow_write"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "ingest",
            {
                "task": task,
            },
        )

    @staticmethod
    def _plan_rollback(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Analizar rollback de forma segura"

        plan.execution_mode = "single"

        plan.context_requirements["project"] = True
        plan.context_requirements["engram"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "task_agent",
            {
                "task": (
                    task + "\n\n"
                    "No borres archivos ni ejecutes "
                    "un rollback destructivo. "
                    "Describe qué se puede revertir "
                    "y los pasos seguros. "
                    "Espera confirmación explícita "
                    "antes de aplicar cambios."
                )
            },
        )

    @staticmethod
    def _plan_analyze_metrics(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Analizar métricas / rendimiento"

        plan.execution_mode = "single"

        plan.context_requirements["project"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "architect",
            {
                "task": task,
                "mode": "metrics",
            },
        )

    # =========================================================
    # LLM planning
    # =========================================================

    @classmethod
    def _generate_steps_with_llm(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        logger.info(
            "Generando pasos con LLM para tarea: %s",
            task[:100],
        )

        known_agents = ", ".join(sorted(cls.KNOWN_AGENTS))

        known_skills = ", ".join(sorted(cls.KNOWN_SKILLS))

        prompt = f"""
Eres un planificador de software.

Genera un plan de ejecución para la siguiente tarea.

Tarea:

{task}

Intención:

{intent.intent}

Dominio:

{intent.domain}

Reglas obligatorias:

- Solo unit_type: "agent" o "skill"
- Agents permitidos: {known_agents}
- Skills permitidas: {known_skills}
- No inventes nombres de agentes ni skills
- No generes contenido de archivos
- Skills actúan; Agents razonan
- Devuelve SOLO un JSON: lista de pasos

Cada paso:

- "description": string
- "unit_type": "agent" | "skill"
- "unit_name": string
- "params": objeto
- "depends_on_index": lista de índices 0-based
"""

        try:
            response = LLMRouter().generate(
                plan=plan,
                context={
                    "instruction": prompt,
                    "task": task,
                },
            )

            steps = cls._parse_steps_from_response(response)

            if not steps:
                logger.warning("El LLM no generó pasos válidos.")
                return

            created_steps: list[tuple[Any, list[int], int]] = []

            index_map: dict[
                int,
                Any,
            ] = {}

            for original_index, step_data in enumerate(steps):
                if not isinstance(
                    step_data,
                    dict,
                ):
                    continue

                description = str(
                    step_data.get(
                        "description",
                        "Paso sin descripción",
                    )
                ).strip()

                unit_type = cls._normalize(
                    step_data.get(
                        "unit_type",
                        "",
                    )
                )

                unit_name = str(
                    step_data.get(
                        "unit_name",
                        "",
                    )
                ).strip()

                params = step_data.get(
                    "params",
                    {},
                )

                if unit_type not in cls.SUPPORTED_UNIT_TYPES:
                    logger.warning(
                        "Paso LLM descartado: " "unit_type inválido=%s",
                        unit_type,
                    )
                    continue

                if unit_type == "agent" and unit_name not in cls.KNOWN_AGENTS:
                    logger.warning(
                        "Paso LLM descartado: " "agent desconocido=%s",
                        unit_name,
                    )
                    continue

                if unit_type == "skill" and unit_name not in cls.KNOWN_SKILLS:
                    logger.warning(
                        "Paso LLM descartado: " "skill desconocida=%s",
                        unit_name,
                    )
                    continue

                if not unit_name:
                    logger.warning("Paso LLM descartado: " "unit_name vacío.")
                    continue

                if not isinstance(
                    params,
                    dict,
                ):
                    params = {}

                raw_dependencies = step_data.get(
                    "depends_on_index",
                    [],
                )

                if not isinstance(
                    raw_dependencies,
                    list,
                ):
                    raw_dependencies = []

                dependencies: list[int] = []

                for index in raw_dependencies:
                    try:
                        dependencies.append(int(index))
                    except (
                        TypeError,
                        ValueError,
                    ):
                        continue

                step = plan.add_step(
                    description=(description or f"Ejecutar {unit_name}"),
                    unit_type=unit_type,
                    unit_name=unit_name,
                    params=params,
                    expected_output=(f"Resultado de " f"{unit_type}: " f"{unit_name}"),
                    metadata={
                        "source": "llm",
                        "llm_index": original_index,
                    },
                )

                created_steps.append(
                    (
                        step,
                        dependencies,
                        original_index,
                    )
                )

                index_map[original_index] = step

            for (
                step,
                dependency_indexes,
                original_index,
            ) in created_steps:
                for dependency_index in dependency_indexes:
                    if dependency_index == original_index:
                        logger.warning(
                            "Dependencia circular " "consigo mismo descartada " "en step=%s",
                            step.id,
                        )
                        continue

                    dependency_step = index_map.get(dependency_index)

                    if dependency_step is None:
                        logger.warning(
                            "Dependencia LLM " "inexistente: step=%s " "depende de índice=%s",
                            step.id,
                            dependency_index,
                        )
                        continue

                    dependency_position = next(
                        (
                            idx
                            for idx, item in enumerate(created_steps)
                            if item[0].id == dependency_step.id
                        ),
                        None,
                    )

                    current_position = next(
                        (idx for idx, item in enumerate(created_steps) if item[0].id == step.id),
                        None,
                    )

                    if (
                        dependency_position is None
                        or current_position is None
                        or dependency_position >= current_position
                    ):
                        logger.warning(
                            "Dependencia no válida " "por orden: step=%s " "depende de índice=%s",
                            step.id,
                            dependency_index,
                        )
                        continue

                    cls._add_dependency(
                        step,
                        dependency_step,
                    )

            logger.info(
                "Pasos generados con LLM: %d",
                len(plan.steps),
            )

        except Exception as exc:
            logger.exception(
                "Error generando pasos con LLM: %s",
                exc,
            )

    @staticmethod
    def _parse_steps_from_response(
        response: str,
    ) -> list[dict[str, Any]]:
        if not isinstance(
            response,
            str,
        ):
            return []

        cleaned = response.strip()

        try:
            data = json.loads(cleaned)

            if isinstance(
                data,
                list,
            ):
                return [
                    item
                    for item in data
                    if isinstance(
                        item,
                        dict,
                    )
                ]

        except json.JSONDecodeError:
            pass

        fenced = re.search(
            r"```(?:json)?\s*(\[.*?\])\s*```",
            cleaned,
            re.DOTALL | re.IGNORECASE,
        )

        if fenced:
            try:
                data = json.loads(fenced.group(1))

                if isinstance(
                    data,
                    list,
                ):
                    return [
                        item
                        for item in data
                        if isinstance(
                            item,
                            dict,
                        )
                    ]

            except json.JSONDecodeError:
                pass

        start = cleaned.find("[")
        end = cleaned.rfind("]") + 1

        if start == -1 or end <= start:
            logger.warning("No se encontró JSON en la " "respuesta del LLM.")
            return []

        json_str = cleaned[start:end]

        try:
            data = json.loads(json_str)

            if not isinstance(
                data,
                list,
            ):
                logger.warning("El JSON no es una lista " "de pasos.")
                return []

            return [
                item
                for item in data
                if isinstance(
                    item,
                    dict,
                )
            ]

        except json.JSONDecodeError:
            logger.warning("Error parseando JSON de la " "respuesta del LLM.")
            return []

    # =========================================================
    # Legacy / compatibility helper
    # =========================================================

    def _extract_write_path(
        self,
        task: str,
        entities: dict | None = None,
    ) -> Optional[str]:
        """
        Extrae el path de escritura de forma segura.

        Mantiene compatibilidad con código que todavía
        invoque este método, pero utiliza la misma lógica
        centralizada de sanitización.
        """
        if not task:
            return None

        path = self._extract_file_path(task)

        if entities:
            for key in (
                "path",
                "filepath",
                "file",
                "output_path",
            ):
                value = entities.get(key)

                if not isinstance(
                    value,
                    str,
                ):
                    continue

                value = value.strip()

                if not value:
                    continue

                if self._looks_like_url(value):
                    continue

                sanitized = self._sanitize_output_path(value)

                if sanitized:
                    return sanitized

        return path or None

    # =========================================================
    # Landing detection
    # =========================================================

    @classmethod
    def _is_multi_phase_landing_request(
        cls,
        task: str,
    ) -> bool:
        """
        Detecta el patrón:

        URL
        +
        análisis
        +
        generación de landing/código
        +
        intención de escritura/materialización.
        """

        task_lower = (task or "").lower()

        has_url = bool(
            re.search(
                r"https?://[^\s]+",
                task,
                re.IGNORECASE,
            )
        )

        has_analyze = bool(
            re.search(
                r"\b("
                r"analiza|"
                r"analizar|"
                r"analisis|"
                r"extrae|"
                r"extraer|"
                r"describe|"
                r"describir|"
                r"estructura|"
                r"estructurar"
                r")\b",
                task_lower,
            )
        )

        has_generate = bool(
            re.search(
                r"\b("
                r"genera|"
                r"generar|"
                r"crea|"
                r"crear|"
                r"escribe|"
                r"escribir|"
                r"landing"
                r")\b",
                task_lower,
            )
        )

        has_write = bool(
            re.search(
                r"\b("
                r"archivo|"
                r"write_file|"
                r"escribe|"
                r"escribir|"
                r"guarda|"
                r"guardar|"
                r"crea|"
                r"crear|"
                r"genera|"
                r"generar"
                r")\b",
                task_lower,
            )
            or re.search(
                r"\bpath\s*[:=]",
                task_lower,
            )
        )

        return has_url and has_analyze and has_generate and has_write
