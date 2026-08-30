from __future__ import annotations

import logging
import re
from typing import Any

from core.execution_plan import ExecutionPlan
from core.intent import IntentResult

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Constructor declarativo de ExecutionPlans.
    """

    name = "execution_planner"

    SUPPORTED_UNIT_TYPES = {"agent", "skill"}

    KNOWN_INTENTS = frozenset(
        {
            "conversation",
            "file_creation",
            "code_generation",
            "project_analysis",
            "project_creation",
            "module_scaffold",
            "ui_scaffold",
            "architecture_audit",
            "quality_audit",
            "security_audit",
            "performance_audit",
            "testing",
            "documentation",
            "refactor",
            "debug",
            "command_execution",
            "docker",
            "spec",
            "planning",
            "analyze_metrics",
            "consolidation",
            "rollback",
        }
    )

    @classmethod
    def create(
        cls,
        task: str,
        intent: IntentResult | dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        if not task or not str(task).strip():
            raise ValueError("ExecutionPlanner requiere una tarea.")

        task = str(task).strip()
        intent_result = cls._normalize_intent(intent)
        intent_name = cls._normalize(intent_result.intent or "conversation")
        domain = cls._normalize(intent_result.domain or "general")
        category = cls._normalize(
            getattr(intent_result, "category", None) or intent_result.domain or "general"
        )
        complexity = cls._normalize(getattr(intent_result, "complexity", None) or "normal")

        intent_category = category
        if intent_name in {
            "file_creation",
            "code_generation",
            "module_scaffold",
            "ui_scaffold",
            "project_creation",
            "refactor",
            "debug",
        }:
            intent_category = "code"
        elif intent_name in {
            "project_analysis",
            "architecture_audit",
            "quality_audit",
            "security_audit",
            "performance_audit",
            "analyze_metrics",
        }:
            intent_category = "analysis"
        elif intent_name in {"spec", "planning", "documentation"}:
            intent_category = "documentation"
        elif intent_name == "conversation":
            intent_category = "conversation"

        plan = ExecutionPlan(original_task=task)
        plan.intent = intent_name
        plan.intent_category = intent_category
        plan.objective = getattr(intent_result, "objective", None) or f"Resolver: {task[:120]}"

        entities = getattr(intent_result, "entities", None) or {}
        if isinstance(entities, dict):
            plan.params.update(entities)

        plan.metadata.update(
            {
                "planner": cls.name,
                "intent": intent_name,
                "domain": domain,
                "complexity": complexity,
                "confidence": getattr(intent_result, "confidence", 0.0),
            }
        )

        if complexity in {"high", "complex"}:
            plan.execution_mode = "multi_step"
        else:
            plan.execution_mode = "single"

        method_name = f"_plan_{intent_name}"
        planner_method = getattr(cls, method_name, None)
        if planner_method is None:
            logger.warning(
                "Intent sin planner dedicado=%s → conversation",
                intent_name,
            )
            planner_method = cls._plan_conversation

        planner_method(plan, task, intent_result)

        errors = plan.validate()
        if errors:
            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        if hasattr(plan, "mark_planned"):
            plan.mark_planned()

        logger.info(
            "ExecutionPlan creado | intent=%s | category=%s | mode=%s | steps=%d",
            intent_name,
            plan.intent_category,
            plan.execution_mode,
            len(plan.steps or []),
        )
        return plan

    # =========================================================
    # Planners
    # =========================================================

    @classmethod
    def _plan_conversation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Responder en conversación"
        plan.execution_mode = "single"
        plan.context_requirements["memory"] = True
        plan.context_requirements["project"] = False
        plan.set_execution_unit(
            unit_type="agent",
            unit_name="multi_turn",
            params={"task": task},
        )
        plan.execution_policy["max_retries"] = 0

    @classmethod
    def _plan_file_creation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        """
        Creación de archivo / landing.
        Multi-phase si hay URL + análisis + generación.
        """
        plan.intent_category = "code"
        plan.metadata["lean_prompt"] = True
        plan.governance["allow_write"] = True
        plan.execution_policy["max_retries"] = 1
        plan.context_requirements["project"] = False
        plan.context_requirements["standards"] = True

        entities = getattr(intent, "entities", None) or {}
        path = (
            entities.get("file") or entities.get("path") or cls._extract_path(task) or "output.txt"
        )

        if cls._is_multi_phase_landing_request(task):
            plan.execution_mode = "multi_step"
            plan.objective = f"Analizar URL y generar {path}"

            scrape = plan.add_step(
                description="Obtener contenido de la URL de referencia",
                unit_type="skill",
                unit_name="scrape_job",
                params={"task": task, "url": cls._extract_url(task)},
                expected_output="Texto/estructura de la página",
                metadata={"stage": "scrape", "produces": "dependency_text"},
                timeout=90,
            )
            gen = plan.add_step(
                description=f"Generar contenido para {path}",
                unit_type="agent",
                unit_name="coder",
                params={"task": task, "path": path},
                expected_output="code_artifact",
                metadata={"stage": "generation", "produces": "code_artifact"},
                timeout=180,
            )
            write = plan.add_step(
                description=f"Escribir {path}",
                unit_type="skill",
                unit_name="write_file",
                params={"path": path, "file_index": 0},
                expected_output=f"Archivo {path}",
                metadata={"stage": "materialization", "consumes": "code_artifact"},
                timeout=60,
            )
            gen.depends_on.append(scrape.id)
            write.depends_on.append(gen.id)
            cls._mark_data_flow(scrape, produces="dependency_text")
            cls._mark_data_flow(gen, produces="code_artifact", consumes="dependency_text")
            return

        plan.execution_mode = "multi_step"
        plan.objective = f"Crear archivo {path}"
        gen = plan.add_step(
            description=f"Generar contenido para {path}",
            unit_type="agent",
            unit_name="coder",
            params={"task": task, "path": path},
            expected_output="code_artifact",
            metadata={"stage": "generation", "produces": "code_artifact"},
            timeout=180,
        )
        write = plan.add_step(
            description=f"Escribir {path}",
            unit_type="skill",
            unit_name="write_file",
            params={"path": path, "file_index": 0},
            expected_output=f"Archivo {path}",
            metadata={"stage": "materialization", "consumes": "code_artifact"},
            timeout=60,
        )
        write.depends_on.append(gen.id)

    @classmethod
    def _plan_code_generation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        path = cls._extract_path(task)
        if path or cls._looks_like_write_request(task):
            cls._plan_file_creation(plan, task, intent)
            return

        plan.intent_category = "code"
        plan.metadata["lean_prompt"] = True
        plan.execution_mode = "single"
        plan.context_requirements["standards"] = True
        plan.context_requirements["project"] = False
        plan.set_execution_unit(
            unit_type="agent",
            unit_name="coder",
            params={"task": task},
        )
        plan.execution_policy["max_retries"] = 1

    @classmethod
    def _plan_project_analysis(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Analizar y resumir el proyecto o directorio"
        plan.execution_mode = "multi_step"
        plan.intent_category = "analysis"
        plan.context_requirements["project"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True
        plan.execution_policy["max_retries"] = 1

        entities = getattr(intent, "entities", None) or {}
        path = entities.get("path") or entities.get("directory") or None

        inspect = plan.add_step(
            description="Inspeccionar estructura y componentes del proyecto",
            unit_type="skill",
            unit_name="analyze_project",
            params={
                "path": path,
                "task": task,
                "prefer_target": True,
            },
            expected_output="Snapshot estructurado del proyecto",
            metadata={"stage": "inspection"},
            timeout=90,
        )
        cls._mark_data_flow(inspect, produces="project_analysis")

        architect = plan.add_step(
            description="Interpretar evidencia y generar resumen ejecutivo",
            unit_type="agent",
            unit_name="architect",
            params={"task": task},
            expected_output="Resumen ejecutivo del proyecto",
            metadata={"stage": "architecture_analysis"},
            timeout=180,
        )
        cls._add_dependency(architect, inspect)
        cls._mark_data_flow(
            architect,
            consumes="project_analysis",
            consumes_from=inspect,
        )

    @classmethod
    def _plan_project_creation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.intent_category = "code"
        plan.execution_mode = "single"
        plan.governance["allow_write"] = True
        plan.governance["allow_shell"] = True
        entities = getattr(intent, "entities", None) or {}
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="create_project",
            params={
                "task": task,
                "name": entities.get("project_name") or entities.get("name"),
                "framework": entities.get("framework") or entities.get("stack"),
            },
        )

    @classmethod
    def _plan_module_scaffold(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.intent_category = "code"
        plan.execution_mode = "single"
        plan.governance["allow_write"] = True
        entities = getattr(intent, "entities", None) or {}
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="scaffold_module",
            params={
                "module": entities.get("module") or "pos",
                "locale": entities.get("locale") or "",
            },
        )

    @classmethod
    def _plan_ui_scaffold(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.intent_category = "code"
        plan.execution_mode = "single"
        plan.governance["allow_write"] = True
        entities = getattr(intent, "entities", None) or {}
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="scaffold_ui_shell",
            params={
                "variant": entities.get("variant") or "pos",
                "locale": entities.get("locale") or "",
            },
        )

    @classmethod
    def _plan_architecture_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_audit(plan, task, "architecture_audit")

    @classmethod
    def _plan_quality_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_audit(plan, task, "quality_audit")

    @classmethod
    def _plan_security_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_audit(plan, task, "security_audit")

    @classmethod
    def _plan_performance_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_audit(plan, task, "performance_audit")

    @classmethod
    def _plan_audit(
        cls,
        plan: ExecutionPlan,
        task: str,
        skill_name: str,
    ) -> None:
        plan.intent_category = "analysis"
        plan.execution_mode = "single"
        plan.context_requirements["project"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name=skill_name,
            params={"task": task},
        )

    @classmethod
    def _plan_testing(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.intent_category = "testing"
        plan.execution_mode = "single"
        plan.governance["allow_shell"] = True
        plan.context_requirements["project"] = False
        
        from core.discovery.engine import DiscoveryEngine
        from core.config import Config
        root = Config.TARGET_PROJECT_ROOT.expanduser().resolve()
        env = DiscoveryEngine(root).discover()
        
        test_cmds = env.commands.get("test", [])
        if not test_cmds:
            plan.status = "not_available"
            plan.error = "No test command could be determined from project evidence."
            return
            
        test_cmd = test_cmds[0].value
        cmd = f'cd "{root}" && ' + test_cmd
        
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="shell",
            params={"command": cmd},
        )

    @classmethod
    def _plan_documentation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.intent_category = "documentation"
        plan.execution_mode = "single"
        plan.context_requirements["project"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="readme",
            params={"task": task},
        )

    @classmethod
    def _plan_spec(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_conversation(plan, task, intent)
        plan.intent = "spec"
        plan.intent_category = "documentation"

    @classmethod
    def _plan_planning(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_conversation(plan, task, intent)
        plan.intent = "planning"
        plan.intent_category = "documentation"

    @classmethod
    def _plan_refactor(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.intent_category = "code"
        plan.metadata["lean_prompt"] = True
        plan.execution_mode = "single"
        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="refactor_code",
            params={"task": task},
        )

    @classmethod
    def _plan_debug(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.intent_category = "code"
        plan.context_requirements["project"] = True
        plan.set_execution_unit(
            unit_type="agent",
            unit_name="task_agent",
            params={"task": task},
        )

    @classmethod
    def _plan_command_execution(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.governance["allow_shell"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="shell",
            params={"command": task},
        )

    @classmethod
    def _plan_docker(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.governance["allow_shell"] = True
        plan.set_execution_unit(
            unit_type="skill",
            unit_name="shell",
            params={"command": task},
        )

    @classmethod
    def _plan_analyze_metrics(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        if re.search(
            r"\b(proyecto|directorio|código|codigo|arquitectura|módulos|modulos)\b",
            task.lower(),
        ):
            cls._plan_project_analysis(plan, task, intent)
            return
        plan.intent_category = "analysis"
        plan.set_execution_unit(
            unit_type="agent",
            unit_name="task_agent",
            params={"task": task},
        )

    @classmethod
    def _plan_consolidation(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_conversation(plan, task, intent)

    @classmethod
    def _plan_rollback(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        cls._plan_conversation(plan, task, intent)

    # =========================================================
    # Helpers
    # =========================================================

    @classmethod
    def _normalize_intent(
        cls,
        intent: IntentResult | dict[str, Any] | None,
    ) -> IntentResult:
        if intent is None:
            return IntentResult(
                intent="conversation",
                domain="general",
                category="general",
                complexity="normal",
                confidence=0.0,
            )
        if isinstance(intent, IntentResult):
            return intent
        if isinstance(intent, dict):
            return IntentResult(
                intent=intent.get("intent", "conversation"),
                domain=intent.get("domain", "general"),
                category=intent.get("category", "general"),
                complexity=intent.get("complexity", "normal"),
                confidence=float(intent.get("confidence") or 0.0),
                entities=intent.get("entities") or {},
                signals=intent.get("signals") or [],
                metadata=intent.get("metadata") or {},
            )
        raise TypeError("intent debe ser IntentResult o dict.")

    @staticmethod
    def _normalize(value: str | None) -> str:
        return str(value or "").strip().lower().replace("-", "_")

    @staticmethod
    def _add_dependency(step: Any, dependency: Any) -> None:
        dep_id = getattr(dependency, "id", dependency)
        deps = getattr(step, "depends_on", None)
        if deps is None:
            step.depends_on = [dep_id]
        elif dep_id not in deps:
            deps.append(dep_id)

    @staticmethod
    def _mark_data_flow(
        step: Any,
        *,
        produces: str | None = None,
        consumes: str | None = None,
        consumes_from: Any = None,
    ) -> None:
        meta = getattr(step, "metadata", None)
        if meta is None:
            step.metadata = {}
            meta = step.metadata
        if produces:
            meta["produces"] = produces
        if consumes:
            meta["consumes"] = consumes
        if consumes_from is not None:
            meta["consumes_from"] = getattr(consumes_from, "id", consumes_from)

    @staticmethod
    def _extract_path(task: str) -> str | None:
        m = re.search(
            r"(?:path\s*[:=]\s*|archivo\s+)['\"]?([A-Za-z0-9_./\\-]+\.[A-Za-z0-9]+)",
            task,
            re.I,
        )
        if m:
            return m.group(1)
        m = re.search(
            r"\b([A-Za-z0-9_./-]+\.(?:html?|py|js|ts|tsx|jsx|css|md|json|vue))\b",
            task,
            re.I,
        )
        return m.group(1) if m else None

    @staticmethod
    def _extract_url(task: str) -> str | None:
        m = re.search(r"https?://[^\s\]\)]+", task)
        return m.group(0) if m else None

    @staticmethod
    def _looks_like_write_request(task: str) -> bool:
        t = task.lower()
        return bool(
            re.search(
                r"\b(crea|crear|genera|generar|escribe|escribir|guarda|guardar|write_file)\b",
                t,
            )
        )

    @classmethod
    def _is_multi_phase_landing_request(cls, task: str) -> bool:
        task_lower = (task or "").lower()
        has_url = bool(re.search(r"https?://[^\s]+", task, re.I))
        has_analyze = bool(
            re.search(
                r"\b(analiza|analizar|analisis|análisis|extrae|extraer|describe)\b",
                task_lower,
            )
        )
        has_generate = bool(
            re.search(
                r"\b(genera|generar|crea|crear|escribe|landing)\b",
                task_lower,
            )
        )
        has_write = bool(
            re.search(
                r"\b(archivo|write_file|guarda|guardar|path\s*[:=])\b",
                task_lower,
            )
            or cls._extract_path(task)
        )
        return has_url and has_analyze and has_generate and has_write
 