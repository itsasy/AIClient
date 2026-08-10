from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.execution_plan import ExecutionPlan
from core.intent import IntentResult
from llm.router import LLMRouter

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Constructor declarativo de ExecutionPlans.

    El ExecutionPlanner decide CÓMO debe ejecutarse una intención,
    pero nunca ejecuta Agents ni Skills.

    Responsabilidades:
        - Traducir una intención a un ExecutionPlan.
        - Definir las unidades ejecutables.
        - Definir dependencias entre steps.
        - Definir parámetros de ejecución.
        - Definir el contexto requerido.
        - Definir governance.
        - Generar pasos mediante LLM cuando corresponda.

    No:
        - ejecuta skills;
        - ejecuta agents;
        - gestiona lifecycle de ejecución;
        - analiza lenguaje natural;
        - descubre Agents;
        - descubre Skills.
    """

    name = "execution_planner"

    SUPPORTED_UNIT_TYPES = {
        "agent",
        "skill",
    }

    # =========================================================
    # Public API
    # =========================================================

    @classmethod
    def create(
        cls,
        task: str,
        intent: IntentResult | dict[str, Any] | None = None,
    ) -> ExecutionPlan:
        """
        Construye un ExecutionPlan a partir de una tarea e intención.

        El planner no ejecuta nada.
        """
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

        if complexity in {"high", "complex"}:
            plan.execution_mode = "multi_step"
        else:
            plan.execution_mode = "single"

        planner_method = getattr(cls, f"_plan_{intent_name}", None)

        if planner_method is None:
            logger.warning(
                "Intent no soportado=%s → fallback conversation",
                intent_name,
            )
            planner_method = cls._plan_conversation

        planner_method(plan, task, intent_result)

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

        for index, step in enumerate(plan.steps, start=1):
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
        """
        Normaliza el input del planner a IntentResult.

        IntentResult NO tiene objective ni constraints.
        Esos campos viven en ExecutionPlan.
        """
        if isinstance(intent, IntentResult):
            return intent

        if isinstance(intent, dict):
            return IntentResult(
                intent=intent.get("intent", "conversation"),
                domain=intent.get("domain", "general"),
                category=intent.get("category", "general"),
                complexity=intent.get("complexity", "normal"),
                confidence=float(intent.get("confidence", 0.0) or 0.0),
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
    def _normalize(value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().lower()

    @staticmethod
    def _extract_file_path(task: str) -> str:
        if not isinstance(task, str):
            return ""

        patterns = (
            r"\bel\s+archivo\s+[\"']([^\"']+)[\"']",
            r"\barchivo\s+[\"']([^\"']+)[\"']",
            r"\bel\s+archivo\s+([^\s\"']+)",
            r"\barchivo\s+([^\s\"']+)",
            r"\b(?:crea|crear|genera|generar|escribe|escribir)\s+(?:un\s+|una\s+)?([^\s\"']+\.[a-zA-Z0-9]+)",
            r"\b([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+)\b",
        )

        structural_words = {
            "con",
            "contenido",
            "que",
            "contenga",
            "conteniendo",
            "un",
            "una",
            "el",
            "la",
        }

        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if not match:
                continue

            path = match.group(1).strip()
            if not path:
                continue
            if path.lower() in structural_words:
                continue
            return path

        return ""

    @staticmethod
    def _extract_file_content(task: str) -> str:
        if not isinstance(task, str):
            return ""

        patterns = (
            r"con el contenido\s+(.+)$",
            r"con contenido\s+(.+)$",
            r"que contenga\s+(.+)$",
            r"conteniendo\s+(.+)$",
        )

        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
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

        if not isinstance(params, dict):
            raise TypeError("params debe ser un diccionario.")

        if plan.is_single():
            plan.set_execution_unit(
                unit_type=unit_type,
                unit_name=unit_name,
                params=params,
            )
            return

        plan.add_step(
            description=f"Ejecutar {unit_type}: {unit_name}",
            unit_type=unit_type,
            unit_name=unit_name,
            params=params,
            expected_output=f"Resultado de {unit_type}: {unit_name}",
        )

    # =========================================================
    # Planning strategies
    # =========================================================

    @staticmethod
    def _plan_project_creation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Crear un nuevo proyecto de software"
        plan.execution_mode = "multi_step"

        framework = intent.get_entity("framework", "unknown")
        name = intent.get_entity("name", "mi_proyecto")

        plan.context_requirements["project"] = False
        plan.context_requirements["gentleman"] = True
        plan.governance["allow_write"] = True

        analyze = plan.add_step(
            description=f"Analizar requisitos para proyecto {framework}",
            unit_type="agent",
            unit_name="architect",
            params={"task": task, "framework": framework},
            expected_output="Decisiones arquitectónicas y requisitos estructurados.",
        )

        generate = plan.add_step(
            description=f"Generar estructura inicial para {framework}",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
                "framework": framework,
                "project_name": name,
            },
            expected_output="Estructura inicial y código base del proyecto.",
        )
        generate.depends_on.append(analyze.id)

        create = plan.add_step(
            description=f"Materializar proyecto {name}",
            unit_type="skill",
            unit_name="create_project",
            params={
                "framework": framework,
                "name": name,
                "task": task,
            },
            expected_output="Proyecto creado en disco.",
        )
        create.depends_on.append(generate.id)

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
            {"task": task},
        )

    @staticmethod
    def _plan_debug(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Analizar y resolver problema técnico"
        plan.execution_mode = "multi_step"
        plan.context_requirements["project"] = True
        plan.context_requirements["engram"] = True

        analyze = plan.add_step(
            description="Analizar problema",
            unit_type="agent",
            unit_name="coder",
            params={"task": task},
            expected_output="Diagnóstico técnico del problema.",
        )

        validate = plan.add_step(
            description="Ejecutar validaciones",
            unit_type="skill",
            unit_name="sandbox",
            params={"task": task},
            expected_output="Resultado de validaciones.",
        )
        validate.depends_on.append(analyze.id)

    @staticmethod
    def _plan_refactor(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Refactorizar código existente"
        plan.execution_mode = "multi_step"
        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True
        plan.governance["allow_write"] = True

        analyze = plan.add_step(
            description="Analizar arquitectura actual",
            unit_type="agent",
            unit_name="architect",
            params={"task": task},
            expected_output="Análisis arquitectónico y estrategia de refactorización.",
        )

        modify = plan.add_step(
            description="Aplicar cambios",
            unit_type="agent",
            unit_name="coder",
            params={"task": task},
            expected_output="Código refactorizado conforme a la estrategia.",
        )
        modify.depends_on.append(analyze.id)

    @staticmethod
    def _plan_project_analysis(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Analizar la arquitectura del proyecto"
        plan.execution_mode = "multi_step"
        plan.context_requirements["project"] = True
        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        inspect = plan.add_step(
            description="Inspeccionar estructura, archivos y componentes del proyecto",
            unit_type="skill",
            unit_name="analyze_project",
            params={"path": ".", "task": task},
            expected_output="Snapshot estructurado del proyecto.",
            metadata={
                "stage": "inspection",
                "produces_context": True,
                "context_key": "project_analysis",
            },
        )

        architect = plan.add_step(
            description=(
                "Interpretar la arquitectura del proyecto " "y generar un resumen ejecutivo"
            ),
            unit_type="agent",
            unit_name="architect",
            params={"task": task},
            expected_output="Análisis arquitectónico ejecutivo del proyecto.",
            metadata={
                "stage": "architecture_analysis",
                "consumes_context": True,
                "context_source": "project_analysis",
            },
        )
        architect.depends_on.append(inspect.id)

    @staticmethod
    def _plan_documentation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Crear documentación"
        plan.context_requirements["project"] = True
        plan.context_requirements["standards"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "task_agent",
            {"task": task, "mode": "documentation"},
        )

    @staticmethod
    def _plan_file_creation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        """
        Si el contenido viene explícito en la tarea → write_file directo.
        Si no → coder produce code_artifact y write_file lo materializa.
        """
        plan.objective = "Crear archivo"
        plan.context_requirements["project"] = True
        plan.governance["allow_write"] = True

        path = ExecutionPlanner._extract_file_path(task)
        if not path:
            path = intent.get_entity("path", "")
        if not path or not path.strip():
            path = "archivo.txt"
        path = path.strip()

        content = ExecutionPlanner._extract_file_content(task)

        # Contenido explícito → un solo step determinista
        if content:
            plan.execution_mode = "single"
            ExecutionPlanner._set_execution_unit(
                plan,
                "skill",
                "write_file",
                {"path": path, "content": content},
            )
            logger.info(
                "File creation (explicit content) | path=%s | content_length=%d",
                path,
                len(content),
            )
            return

        # Sin contenido → coder genera, write_file escribe
        plan.execution_mode = "multi_step"

        coder_step = plan.add_step(
            description=f"Generar contenido para {path}",
            unit_type="agent",
            unit_name="coder",
            params={"task": task, "path": path},
            expected_output="code_artifact con path y content.",
        )

        write_step = plan.add_step(
            description=f"Escribir archivo {path}",
            unit_type="skill",
            unit_name="write_file",
            params={},  # path/content llegan por materialización
            expected_output="Archivo creado en disco.",
        )
        write_step.depends_on.append(coder_step.id)

        logger.info(
            "File creation (coder→write_file) | path=%s",
            path,
        )

    @staticmethod
    def _plan_command_execution(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Ejecutar comando"
        plan.context_requirements["project"] = True
        plan.governance["allow_shell"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "shell",
            {"task": task},
        )

    @staticmethod
    def _plan_docker(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Operación Docker"
        plan.context_requirements["project"] = True
        plan.governance["allow_shell"] = True
        plan.governance["allow_network"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "sandbox",
            {"task": task},
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

        spec_step = plan.add_step(
            description="Generar especificación detallada a partir de la tarea",
            unit_type="agent",
            unit_name="task_agent",
            params={"task": task, "mode": "spec"},
            expected_output="Especificación estructurada.",
            metadata={"stage": "spec_generation"},
        )

        write_spec = plan.add_step(
            description="Guardar especificación en disco",
            unit_type="skill",
            unit_name="write_file",
            params={"task": task, "mode": "spec"},
            expected_output="Archivo de especificación creado.",
        )
        write_spec.depends_on.append(spec_step.id)

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
        cls._generate_steps_with_llm(plan, task, intent)

    @staticmethod
    def _plan_conversation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        """
        Conversación pura:
            - sin contexto de proyecto / Obsidian / Engram
            - multi_turn
        """
        plan.objective = task
        plan.execution_mode = "single"

        for key in plan.context_requirements:
            plan.context_requirements[key] = False

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "multi_turn",
            {"task": task},
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
        logger.info("Generando pasos con LLM para tarea: %s", task[:100])

        prompt = f"""
Eres un planificador de software.

Genera un plan de ejecución para la siguiente tarea.

Tarea:
{task}

Intención:
{intent.intent}

Dominio:
{intent.domain}

Los únicos tipos de unidad permitidos son:
- agent
- skill

No inventes nombres de agentes ni skills.
Usa solo: architect, coder, multi_turn, task_agent,
analyze_project, write_file, create_project, sandbox.

Devuelve SOLO un JSON con una lista de pasos.

Cada paso debe tener:
- "description": descripción clara
- "unit_type": "agent" o "skill"
- "unit_name": nombre de la unidad
- "params": objeto con parámetros opcionales

Ejemplo:
[
  {{
    "description": "Analizar requisitos",
    "unit_type": "agent",
    "unit_name": "architect",
    "params": {{"task": "..."}}
  }},
  {{
    "description": "Generar código",
    "unit_type": "agent",
    "unit_name": "coder",
    "params": {{"task": "..."}}
  }}
]
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

            for step_data in steps:
                if not isinstance(step_data, dict):
                    continue

                description = str(step_data.get("description", "Paso sin descripción")).strip()
                unit_type = cls._normalize(step_data.get("unit_type", ""))
                unit_name = str(step_data.get("unit_name", "")).strip()
                params = step_data.get("params", {})

                if unit_type not in cls.SUPPORTED_UNIT_TYPES:
                    logger.warning(
                        "Paso LLM descartado: unit_type inválido=%s",
                        unit_type,
                    )
                    continue

                if not unit_name:
                    logger.warning("Paso LLM descartado: unit_name vacío.")
                    continue

                if not isinstance(params, dict):
                    params = {}

                plan.add_step(
                    description=description or f"Ejecutar {unit_name}",
                    unit_type=unit_type,
                    unit_name=unit_name,
                    params=params,
                    expected_output=f"Resultado de {unit_type}: {unit_name}",
                    metadata={"source": "llm"},
                )

            logger.info("Pasos generados con LLM: %d", len(plan.steps))

        except Exception as exc:
            logger.exception("Error generando pasos con LLM: %s", exc)

    @staticmethod
    def _parse_steps_from_response(response: str) -> list[dict[str, Any]]:
        if not isinstance(response, str):
            return []

        start = response.find("[")
        end = response.rfind("]") + 1
        if start == -1 or end <= start:
            logger.warning("No se encontró JSON en la respuesta del LLM.")
            return []

        json_str = response[start:end]

        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                logger.warning("El JSON no es una lista de pasos.")
                return []
            return [item for item in data if isinstance(item, dict)]
        except json.JSONDecodeError:
            logger.warning("Error parseando JSON de la respuesta del LLM.")
            return []
