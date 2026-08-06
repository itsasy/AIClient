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
    - Definir unidad ejecutable.
    - Definir pasos.
    - Definir contexto requerido.

    No:

    - Ejecuta.
    - Selecciona LLM.
    - Ejecuta agentes.
    - Ejecuta skills.
    """

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

        plan.mark_planned()

        return plan

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

        plan.execution_unit_type = "agent"

        plan.execution_unit = "coder"

        plan.params = {
            "task": task,
        }

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

        plan.execution_unit_type = "agent"

        plan.execution_unit = "writer"

        plan.params = {
            "task": task,
        }

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

        plan.execution_unit_type = "skill"

        plan.execution_unit = "write_file"

        plan.params = {
            "task": task,
        }

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

        plan.execution_unit_type = "skill"

        plan.execution_unit = "shell"

        plan.params = {
            "task": task,
        }

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

        plan.execution_unit_type = "skill"

        plan.execution_unit = "sandbox"

        plan.params = {
            "task": task,
        }

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

        plan.execution_unit_type = "agent"

        plan.execution_unit = "task"

        plan.params = {
            "task": task,
        }

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

                plan.add_context_requirement(provider)
