from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan

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

    No:
        - Ejecuta skills.
        - Ejecuta agents.
        - Accede directamente al LLM.
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
    ) -> ExecutionPlan:
        if not task or not task.strip():
            raise ValueError("ExecutionPlanner requiere una tarea.")

        intent = intent or {}

        plan = ExecutionPlan(
            original_task=task.strip(),
        )

        intent_name = cls._normalize(
            intent.get("intent", "conversation"),
        )

        domain = cls._normalize(
            intent.get("domain", "general"),
        )

        complexity = cls._normalize(
            intent.get("complexity", "normal"),
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

        if complexity in {"high", "complex"}:
            plan.execution_mode = "multi_step"
        else:
            plan.execution_mode = "single"

        planner_method = getattr(
            cls,
            f"_plan_{intent_name}",
            cls._plan_default,
        )

        planner_method(
            plan,
            task.strip(),
        )

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
    # Project creation
    # ======================================================

    @staticmethod
    def _plan_project_creation(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Crear un nuevo proyecto de software"
        plan.execution_mode = "multi_step"

        analyze = plan.add_step(
            description="Analizar requisitos del proyecto",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
            expected_output=(
                "Decisiones arquitectónicas y requisitos " "estructurados del proyecto."
            ),
        )

        generate = plan.add_step(
            description="Generar estructura inicial",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
            expected_output=("Estructura inicial y código base del proyecto."),
        )

        generate.depends_on.append(
            analyze.id,
        )

    # ======================================================
    # Code generation
    # ======================================================

    @staticmethod
    def _plan_code_generation(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Generar código"

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "coder",
            {
                "task": task,
            },
        )

    # ======================================================
    # Debug
    # ======================================================

    @staticmethod
    def _plan_debug(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Analizar y resolver problema técnico"
        plan.execution_mode = "multi_step"

        analyze = plan.add_step(
            description="Analizar problema",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
            expected_output=("Diagnóstico técnico del problema y propuesta " "de corrección."),
        )

        validate = plan.add_step(
            description="Ejecutar validaciones",
            unit_type="skill",
            unit_name="sandbox",
            params={
                "task": task,
            },
            expected_output=("Resultado de las validaciones y pruebas ejecutadas."),
        )

        validate.depends_on.append(
            analyze.id,
        )

    # ======================================================
    # Refactor
    # ======================================================

    @staticmethod
    def _plan_refactor(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Refactorizar código existente"
        plan.execution_mode = "multi_step"

        analyze = plan.add_step(
            description="Analizar arquitectura actual",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
            expected_output=("Análisis arquitectónico y estrategia de refactorización."),
        )

        modify = plan.add_step(
            description="Aplicar cambios",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
            expected_output=("Código refactorizado conforme a la estrategia definida."),
        )

        modify.depends_on.append(
            analyze.id,
        )

    # ======================================================
    # Project analysis
    # ======================================================

    @staticmethod
    def _plan_project_analysis(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        """
        Construye el pipeline completo de análisis de proyecto.

        El análisis de un proyecto tiene dos responsabilidades
        diferentes:

        1. Inspeccionar físicamente el proyecto.
        2. Interpretar esa información y producir el análisis
           arquitectónico solicitado por el usuario.

        La Skill no debe convertirse en la respuesta final.
        Su resultado alimenta al ArchitectAgent.
        """

        plan.objective = "Analizar la arquitectura del proyecto " "y generar un resumen ejecutivo"

        plan.execution_mode = "multi_step"

        # --------------------------------------------------
        # STEP 1: inspección
        # --------------------------------------------------

        inspect = plan.add_step(
            description=("Inspeccionar estructura, archivos y componentes " "del proyecto"),
            unit_type="skill",
            unit_name="analyze_project",
            params={
                "path": ".",
                "task": task,
            },
            expected_output=(
                "Snapshot estructurado del proyecto con su "
                "estructura, archivos, módulos y contenido relevante."
            ),
            metadata={
                "stage": "inspection",
                "produces_context": True,
                "context_key": "project_analysis",
            },
        )

        # --------------------------------------------------
        # STEP 2: interpretación arquitectónica
        # --------------------------------------------------

        architect = plan.add_step(
            description=(
                "Interpretar la arquitectura del proyecto " "y generar un resumen ejecutivo"
            ),
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
            expected_output=(
                "Análisis arquitectónico ejecutivo del proyecto, "
                "incluyendo estructura, patrones, responsabilidades, "
                "fortalezas, problemas y recomendaciones."
            ),
            metadata={
                "stage": "architecture_analysis",
                "consumes_context": True,
                "context_source": "project_analysis",
            },
        )

        architect.depends_on.append(
            inspect.id,
        )

    # ======================================================
    # Documentation
    # ======================================================

    @staticmethod
    def _plan_documentation(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Crear documentación"

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "writer",
            {
                "task": task,
            },
        )

    # ======================================================
    # File creation
    # ======================================================

    @staticmethod
    def _plan_file_creation(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Crear archivo"

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "write_file",
            {
                "task": task,
            },
        )

    # ======================================================
    # Command execution
    # ======================================================

    @staticmethod
    def _plan_command_execution(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Ejecutar comando"

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "shell",
            {
                "task": task,
            },
        )

    # ======================================================
    # Docker
    # ======================================================

    @staticmethod
    def _plan_docker(
        plan: ExecutionPlan,
        task: str,
    ) -> None:
        plan.objective = "Operación Docker"

        ExecutionPlanner._set_execution_unit(
            plan,
            "skill",
            "sandbox",
            {
                "task": task,
            },
        )

    # ======================================================
    # Default
    # ======================================================

    @staticmethod
    def _plan_default(
        plan: ExecutionPlan,
        task: str,
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
