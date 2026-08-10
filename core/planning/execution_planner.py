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

    El ExecutionPlanner decide COMO debe ejecutarse una intención,
    pero nunca ejecuta Agents ni Skills.

    Responsabilidades:

        - Traducir una intención conocida a un ExecutionPlan.
        - Definir las unidades ejecutables.
        - Definir dependencias entre steps.
        - Definir el resultado esperado de cada step.
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

    # =========================================================
    # Public API
    # =========================================================

    @classmethod
    def create(
        cls,
        task: str,
        intent: IntentResult,
        generate_steps_with_llm: bool = False,
    ) -> ExecutionPlan:
        """
        Crea un ExecutionPlan a partir de una tarea y un IntentResult.
        """

        if not task or not task.strip():
            raise ValueError("ExecutionPlanner requiere una tarea.")

        if not isinstance(intent, IntentResult):
            raise TypeError("ExecutionPlanner requiere un IntentResult.")

        task = task.strip()

        plan = ExecutionPlan(
            original_task=task,
        )

        intent_name = intent.intent
        domain = intent.domain
        complexity = intent.complexity

        plan.intent = intent_name
        plan.intent_category = domain

        plan.metadata.update(
            {
                "planner": cls.name,
                "intent": intent_name,
                "domain": domain,
                "complexity": complexity,
                "intent_confidence": intent.confidence,
                "intent_category": intent.category,
                "intent_signals": list(intent.signals),
            }
        )

        # =====================================================
        # Execution mode
        # =====================================================

        if complexity in {"high", "complex"} or generate_steps_with_llm:
            plan.execution_mode = "multi_step"
        else:
            plan.execution_mode = "single"

        # =====================================================
        # Plan strategy
        # =====================================================

        planner_method = getattr(
            cls,
            f"_plan_{intent_name}",
            cls._plan_default,
        )

        planner_method(
            plan,
            task,
            intent,
        )

        # =====================================================
        # Optional LLM planning
        # =====================================================

        if plan.is_multi_step() and not plan.steps and generate_steps_with_llm:
            cls._generate_steps_with_llm(
                plan,
                task,
                intent,
            )

        # =====================================================
        # Validation
        # =====================================================

        errors = plan.validate()

        if errors:
            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        plan.mark_planned()

        logger.info(
            "ExecutionPlan creado | intent=%s | mode=%s | steps=%d",
            intent_name,
            plan.execution_mode,
            len(plan.steps),
        )

        for index, step in enumerate(
            plan.steps,
            start=1,
        ):
            logger.info(
                "Plan step=%d id=%s unit=%s:%s depends_on=%s",
                index,
                step.id,
                step.unit_type,
                step.unit_name,
                step.depends_on,
            )

        if plan.is_single():
            logger.info(
                "Plan single | unit=%s:%s",
                plan.execution_unit_type,
                plan.execution_unit,
            )

        return plan

    # =========================================================
    # Helpers
    # =========================================================

    @staticmethod
    def _extract_file_path(task: str) -> str:
        """
        Extrae el nombre/ruta explícito del archivo desde una
        instrucción de creación de archivo.

        Ejemplos:

            crea un archivo prueba.txt
            crear archivo config.json
            crea un archivo src/main.py con el contenido ...
            crear el archivo "notas.md" con contenido "hola"

        Devuelve una cadena vacía si no encuentra un path.
        """

        if not isinstance(task, str):
            return ""

        patterns = (
            # archivo "src/test.py"
            r"\barchivo\s+[\"']([^\"']+)[\"']",
            # el archivo "src/test.py"
            r"\bel\s+archivo\s+[\"']([^\"']+)[\"']",
            # archivo src/test.py
            r"\barchivo\s+([^\s\"']+)",
            # el archivo src/test.py
            r"\bel\s+archivo\s+([^\s\"']+)",
        )

        structural_words = {
            "con",
            "contenido",
            "que",
            "contenga",
            "conteniendo",
        }

        for pattern in patterns:
            match = re.search(
                pattern,
                task,
                re.IGNORECASE,
            )

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
        """
        Extrae contenido simple desde una instrucción de creación
        de archivo.
        """

        if not isinstance(task, str):
            return ""

        patterns = (
            r"con el contenido\s+(.+)$",
            r"con contenido\s+(.+)$",
            r"que contenga\s+(.+)$",
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

    @staticmethod
    def _set_execution_unit(
        plan: ExecutionPlan,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        """
        Define una unidad de ejecución.

        En modo single:
            la unidad se almacena directamente en ExecutionPlan.

        En modo multi_step:
            la unidad se representa como un ExecutionStep.
        """

        if unit_type not in {
            "agent",
            "skill",
        }:
            raise ValueError(
                f"Tipo de unidad inválido: {unit_type!r}. " "Debe ser 'agent' o 'skill'."
            )

        if not unit_name or not unit_name.strip():
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

        framework = intent.get_entity(
            "framework",
            "unknown",
        )

        name = intent.get_entity(
            "name",
            "mi_proyecto",
        )

        plan.context_requirements["project"] = False
        plan.context_requirements["gentleman"] = True

        analyze = plan.add_step(
            description=f"Analizar requisitos para proyecto {framework}",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
                "framework": framework,
            },
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
            },
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
            params={
                "task": task,
            },
            expected_output="Diagnóstico técnico del problema.",
        )

        validate = plan.add_step(
            description="Ejecutar validaciones",
            unit_type="skill",
            unit_name="sandbox",
            params={
                "task": task,
            },
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

        analyze = plan.add_step(
            description="Analizar arquitectura actual",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
            expected_output="Análisis arquitectónico y estrategia de refactorización.",
        )

        modify = plan.add_step(
            description="Aplicar cambios",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
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
            params={
                "path": ".",
                "task": task,
            },
            expected_output="Snapshot estructurado del proyecto.",
            metadata={
                "stage": "inspection",
                "produces_context": True,
                "context_key": "project_analysis",
            },
        )

        architect = plan.add_step(
            description="Interpretar la arquitectura del proyecto y generar un resumen ejecutivo",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
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
            "writer",
            {
                "task": task,
            },
        )

    @staticmethod
    def _plan_file_creation(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Crear archivo"

        plan.context_requirements["project"] = True

        # =====================================================
        # Governance
        # =====================================================

        # Crear un archivo es una operación de escritura.
        # El modo safe no implica "sin escritura"; implica que
        # la operación debe quedar explícitamente declarada.
        plan.governance["allow_write"] = True

        # =====================================================
        # Path
        # =====================================================

        # IMPORTANTE:
        #
        # La tarea original es la fuente más específica para
        # identificar el archivo solicitado por el usuario.
        #
        # El IntentResult puede contener entidades inferidas
        # incorrectamente. Por eso el path explícito encontrado
        # en la tarea tiene prioridad.
        path = ExecutionPlanner._extract_file_path(task)

        if not path:
            path = intent.get_entity(
                "path",
                "",
            )

        if not path or not path.strip():
            path = "archivo.txt"

        path = path.strip()

        # =====================================================
        # Content
        # =====================================================

        content = ExecutionPlanner._extract_file_content(task)

        # =====================================================
        # Execution unit
        # =====================================================

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "write_file",
            {
                "path": path,
                "content": content,
            },
        )

        logger.info(
            "File creation plan | path=%s | content_length=%d",
            path,
            len(content),
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
            {
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

        spec_step = plan.add_step(
            description="Generar especificación detallada a partir de la tarea",
            unit_type="agent",
            unit_name="planner",
            params={
                "task": task,
                "mode": "spec",
            },
            expected_output="Especificación estructurada en formato JSON.",
            metadata={
                "stage": "spec_generation",
            },
        )

        write_spec = plan.add_step(
            description="Guardar especificación en disco",
            unit_type="skill",
            unit_name="write_file",
            params={
                "task": task,
                "mode": "spec",
            },
            expected_output="Archivo de especificación creado.",
        )

        write_spec.depends_on.append(spec_step.id)

    @staticmethod
    def _plan_planning(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        plan.objective = "Generar un plan de ejecución"
        plan.execution_mode = "multi_step"

        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        ExecutionPlanner._generate_steps_with_llm(
            plan,
            task,
            intent,
        )

    @staticmethod
    def _plan_default(
        plan: ExecutionPlan,
        task: str,
        intent: IntentResult,
    ) -> None:
        if not plan.intent:
            plan.intent = "conversation"

        plan.objective = task

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "task_agent",
            {
                "task": task,
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

        prompt = f"""
Eres un planificador de software.

Genera un plan de ejecución para la siguiente tarea.

Tarea:
{task}

Intención:
{intent.intent}

Dominio:
{intent.domain}

Devuelve SOLO un JSON con una lista de pasos.

Cada paso debe tener:

- "description": descripción clara
- "unit_type": "agent" o "skill"
- "unit_name": nombre del agente o skill
- "params": objeto con parámetros opcionales

Ejemplo:

[
{{
    "description": "Analizar requisitos",
    "unit_type": "agent",
    "unit_name": "architect",
    "params": {{
        "task": "..."
    }}
}},
{{
    "description": "Generar código",
    "unit_type": "agent",
    "unit_name": "coder",
    "params": {{
        "task": "..."
    }}
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

                description = step_data.get(
                    "description",
                    "Paso sin descripción",
                )

                unit_type = step_data.get(
                    "unit_type",
                    "agent",
                )

                unit_name = step_data.get(
                    "unit_name",
                    "task_agent",
                )

                params = step_data.get(
                    "params",
                    {},
                )

                if not isinstance(params, dict):
                    params = {}

                plan.add_step(
                    description=description,
                    unit_type=unit_type,
                    unit_name=unit_name,
                    params=params,
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
