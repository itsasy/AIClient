from __future__ import annotations

import json
import logging
import re
from typing import Any

from core.execution_plan import ExecutionPlan
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
        - (Opcional) Generar pasos mediante LLM para tareas complejas.

    No:
        - Ejecuta skills.
        - Ejecuta agents.
        - Gestiona el lifecycle de ejecución.
    """

    name = "execution_planner"

    # ======================================================
    # Public API
    # ======================================================

    @classmethod
    def create(
        cls,
        task: str,
        intent: dict[str, Any] | None = None,
        generate_steps_with_llm: bool = False,
    ) -> ExecutionPlan:
        """
        Crea un ExecutionPlan a partir de una tarea y una intención.

        Args:
            task: Tarea original del usuario.
            intent: Diccionario con los datos de IntentResult.
            generate_steps_with_llm: Si es True, usa LLM para generar pasos adicionales.
        """
        if not task or not task.strip():
            raise ValueError("ExecutionPlanner requiere una tarea.")

        intent_data = intent or {}

        plan = ExecutionPlan(
            original_task=task.strip(),
        )

        intent_name = cls._normalize(
            intent_data.get("intent", "conversation"),
        )

        domain = cls._normalize(
            intent_data.get("domain", "general"),
        )

        complexity = cls._normalize(
            intent_data.get("complexity", "normal"),
        )

        plan.intent = intent_name
        plan.intent_category = domain

        plan.metadata.update(
            {
                "planner": cls.name,
                "intent": intent_name,
                "domain": domain,
                "complexity": complexity,
            }
        )

        # Determinar modo de ejecución
        if complexity in {"high", "complex"} or generate_steps_with_llm:
            plan.execution_mode = "multi_step"
        else:
            plan.execution_mode = "single"

        # Construir el plan según el intent
        planner_method = getattr(
            cls,
            f"_plan_{intent_name}",
            cls._plan_default,
        )

        planner_method(
            plan,
            task.strip(),
            intent_data,
        )

        # Si el plan está en multi_step y no tiene pasos, y se solicita LLM, generarlos
        if plan.is_multi_step() and not plan.steps and generate_steps_with_llm:
            cls._generate_steps_with_llm(plan, task, intent_data)

        errors = plan.validate()

        if errors:
            raise ValueError(
                "ExecutionPlan inválido: " + ", ".join(errors),
            )

        plan.mark_planned()

        logger.info(
            "ExecutionPlan creado intent=%s mode=%s steps=%d",
            intent_name,
            plan.execution_mode,
            len(plan.steps),
        )

        for index, step in enumerate(plan.steps, start=1):
            logger.info(
                "Plan step=%d id=%s unit=%s:%s depends_on=%s",
                index,
                step.id,
                step.unit_type,
                step.unit_name,
                step.depends_on,
            )

        return plan

    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def _normalize(
        value: str | None,
    ) -> str:
        if not value:
            return ""

        return value.lower().strip().replace("-", "_").replace(" ", "_")

    @staticmethod
    def _set_execution_unit(
        plan: ExecutionPlan,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        plan.execution_unit_type = ExecutionPlan.normalize_unit_type(unit_type)

        plan.execution_unit = unit_name

        plan.params = params or {}

    # ======================================================
    # Planificación por intent
    # ======================================================

    @staticmethod
    def _plan_project_creation(
        plan: ExecutionPlan,
        task: str,
        intent: dict[str, Any],
    ) -> None:
        plan.objective = "Crear un nuevo proyecto de software"
        plan.execution_mode = "multi_step"

        # Extraer framework y nombre de la entidad
        framework = intent.get("entities", {}).get("framework", "unknown")
        name = intent.get("entities", {}).get("name", "mi_proyecto")

        # Añadir contexto específico
        plan.context_requirements["project"] = False
        plan.context_requirements["gentleman"] = True  # Puede usar skills de framework

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
        intent: dict[str, Any],
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
        intent: dict[str, Any],
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
        intent: dict[str, Any],
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
        intent: dict[str, Any],
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
        intent: dict[str, Any],
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
        intent: dict[str, Any],
    ) -> None:
        plan.objective = "Crear archivo"
        plan.context_requirements["project"] = True

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "write_file",
            {
                "task": task,
            },
        )

    @staticmethod
    def _plan_command_execution(
        plan: ExecutionPlan,
        task: str,
        intent: dict[str, Any],
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
        intent: dict[str, Any],
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
        intent: dict[str, Any],
    ) -> None:
        plan.objective = "Crear especificación (Spec)"
        plan.execution_mode = "multi_step"
        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        # Usamos el generador LLM para crear la Spec
        # El primer paso será generar la spec con un agente especializado
        spec_step = plan.add_step(
            description="Generar especificación detallada a partir de la tarea",
            unit_type="agent",
            unit_name="planner",  # Mantenemos "planner" como nombre, pero ahora es un agente opcional
            params={
                "task": task,
                "mode": "spec",
            },
            expected_output="Especificación estructurada en formato JSON.",
            metadata={
                "stage": "spec_generation",
            },
        )

        # Luego, escribir la spec en disco
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
        intent: dict[str, Any],
    ) -> None:
        plan.objective = "Generar un plan de ejecución"
        plan.execution_mode = "multi_step"
        plan.context_requirements["engram"] = True
        plan.context_requirements["standards"] = True

        # Usar LLM para generar pasos del plan
        ExecutionPlanner._generate_steps_with_llm(plan, task, intent)

    @staticmethod
    def _plan_default(
        plan: ExecutionPlan,
        task: str,
        intent: dict[str, Any],
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

    # ======================================================
    # Generación de pasos con LLM
    # ======================================================

    @classmethod
    def _generate_steps_with_llm(
        cls,
        plan: ExecutionPlan,
        task: str,
        intent: dict[str, Any],
    ) -> None:
        """
        Genera pasos del plan usando el LLM.
        """
        logger.info("Generando pasos con LLM para tarea: %s", task[:100])

        # Construir prompt para el LLM
        prompt = f"""
Eres un planificador de software. Genera un plan de ejecución para la siguiente tarea.

Tarea: {task}

Intención: {intent.get('intent', 'unknown')}
Dominio: {intent.get('domain', 'general')}

Devuelve SOLO un JSON con una lista de pasos.
Cada paso debe tener:
- "description": descripción clara
- "unit_type": "agent" o "skill"
- "unit_name": nombre del agente o skill (architect, coder, shell, write_file, etc.)
- "params": objeto con parámetros (opcional)

Ejemplo:
[
  {{"description": "Analizar requisitos", "unit_type": "agent", "unit_name": "architect", "params": {{"task": "..."}}}},
  {{"description": "Generar código", "unit_type": "agent", "unit_name": "coder", "params": {{"task": "..."}}}}
]
"""

        # Usar LLMRouter para generar los pasos
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
                description = step_data.get("description", "Paso sin descripción")
                unit_type = step_data.get("unit_type", "agent")
                unit_name = step_data.get("unit_name", "task_agent")
                params = step_data.get("params", {})

                plan.add_step(
                    description=description,
                    unit_type=unit_type,
                    unit_name=unit_name,
                    params=params,
                )

            logger.info("Pasos generados con LLM: %d", len(plan.steps))

        except Exception as e:
            logger.exception("Error generando pasos con LLM: %s", e)

    @staticmethod
    def _parse_steps_from_response(response: str) -> list[dict[str, Any]]:
        """
        Extrae la lista de pasos de la respuesta del LLM.
        """
        start = response.find("[")
        end = response.rfind("]") + 1

        if start == -1 or end == -1:
            logger.warning("No se encontró JSON en la respuesta del LLM.")
            return []

        json_str = response[start:end]

        try:
            data = json.loads(json_str)
            if isinstance(data, list):
                return data
            else:
                logger.warning("El JSON no es una lista de pasos.")
                return []
        except json.JSONDecodeError:
            logger.warning("Error parseando JSON de la respuesta del LLM.")
            return []
