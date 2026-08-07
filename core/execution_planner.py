from __future__ import annotations

import logging

from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Construye ExecutionPlans.

    Responsabilidades:

    - Transformar intención en plan.
    - Definir unidades ejecutables.
    - Definir steps.
    - Declarar contexto requerido.
    - Validar estructura inicial.

    No:

    - Ejecuta.
    - Selecciona LLM.
    - Ejecuta agentes.
    - Ejecuta skills.
    """

    # ======================================================
    # Public API
    # ======================================================

    @staticmethod
    def create(
        task: str,
        intent: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ExecutionPlan:

        context = context or {}

        plan = ExecutionPlan(
            original_task=task,
        )

        intent_name = intent.get(
            "intent",
            "conversation",
        )

        domain = intent.get(
            "domain",
            "general",
        )

        complexity = intent.get(
            "complexity",
            "normal",
        )

        plan.intent = intent_name

        plan.intent_category = domain

        plan.planning_metadata = {
            "planner": "execution_planner",
            "intent": intent_name,
            "domain": domain,
            "complexity": complexity,
        }

        if complexity in (
            "high",
            "complex",
        ):
            plan.execution_mode = "multi_step"

        else:
            plan.execution_mode = "single"

        logger.info(
            "Creando plan intent=%s domain=%s complexity=%s",
            intent_name,
            domain,
            complexity,
        )

        planner = getattr(
            ExecutionPlanner,
            f"_plan_{intent_name}",
            ExecutionPlanner._plan_default,
        )

        planner(
            plan,
            task,
            context,
        )

        ExecutionPlanner._apply_context_requirements(
            plan,
            context,
        )

        errors = plan.validate()

        if errors:

            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

        plan.mark_planned()

        plan.status = "validated"

        return plan

    # ======================================================
    # Helpers
    # ======================================================

    @staticmethod
    def _set_execution_unit(
        plan: ExecutionPlan,
        unit_type: str,
        unit_name: str,
        params: dict[str, Any],
    ):

        plan.execution_unit_type = ExecutionPlan.normalize_unit_type(
            unit_type,
        )

        plan.execution_unit = unit_name

        plan.params = params

    # ======================================================
    # PROJECT CREATION
    # ======================================================

    @staticmethod
    def _plan_project_creation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Crear un nuevo proyecto de software"

        plan.execution_mode = "multi_step"

        plan.add_step(
            description="Analizar requisitos del proyecto",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
        )

        plan.add_step(
            description="Generar estructura inicial",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
        )

        plan.steps[1].depends_on.append(
            plan.steps[0].id,
        )

    # ======================================================
    # CODE GENERATION
    # ======================================================

    @staticmethod
    def _plan_code_generation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

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
    # DEBUG
    # ======================================================

    @staticmethod
    def _plan_debug(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Analizar y resolver problema técnico"

        plan.execution_mode = "multi_step"

        plan.add_step(
            description="Analizar problema",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
        )

        plan.add_step(
            description="Ejecutar validaciones",
            unit_type="skill",
            unit_name="sandbox",
            params={
                "task": task,
            },
        )

        plan.steps[1].depends_on.append(
            plan.steps[0].id,
        )

    # ======================================================
    # REFACTOR
    # ======================================================

    @staticmethod
    def _plan_refactor(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Refactorizar código existente"

        plan.execution_mode = "multi_step"

        plan.add_step(
            description="Analizar arquitectura actual",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
        )

        plan.add_step(
            description="Aplicar cambios",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
        )

        plan.steps[1].depends_on.append(
            plan.steps[0].id,
        )

    # ======================================================
    # DOCUMENTATION
    # ======================================================

    @staticmethod
    def _plan_documentation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

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
    # FILE CREATION
    # ======================================================

    @staticmethod
    def _plan_file_creation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

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
    # COMMAND EXECUTION
    # ======================================================

    @staticmethod
    def _plan_command_execution(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

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
    # DOCKER
    # ======================================================

    @staticmethod
    def _plan_docker(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

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
    # DEFAULT
    # ======================================================

    @staticmethod
    def _plan_default(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.intent = "conversation"

        plan.objective = task

        ExecutionPlanner._set_execution_unit(
            plan,
            "agent",
            "task",
            {
                "task": task,
            },
        )

    # ======================================================
    # CONTEXT
    # ======================================================

    @staticmethod
    def _apply_context_requirements(
        plan: ExecutionPlan,
        context: dict[str, Any],
    ):

        available = set(context.keys())

        for provider in (
            "project",
            "memory",
            "engram",
            "documents",
            "standards",
            "knowledge",
            "gentleman",
        ):

            if provider in available:

                plan.add_context_requirement(
                    provider,
                )
