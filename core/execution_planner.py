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
    - Validar estructura inicial.

    No:

    - Ejecuta.
    - Construye contexto.
    - Gestiona memoria.
    - Ejecuta agentes.
    - Ejecuta skills.
    """

    # ======================================================
    # Public API
    # ======================================================

    @staticmethod
    def create(
        task: str,
        intent: dict[str, Any] | None,
    ) -> ExecutionPlan:

        intent = intent or {}

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
            "Creando ExecutionPlan intent=%s domain=%s complexity=%s",
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
    ) -> None:

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
    ) -> None:

        plan.objective = "Crear un nuevo proyecto de software"

        plan.execution_mode = "multi_step"

        first = plan.add_step(
            description="Analizar requisitos del proyecto",
            unit_type="agent",
            unit_name="architect",
            params={
                "task": task,
            },
        )

        second = plan.add_step(
            description="Generar estructura inicial",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
        )

        second.depends_on.append(
            first.id,
        )

    # ======================================================
    # CODE GENERATION
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
    # DEBUG
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
        )

        validate = plan.add_step(
            description="Ejecutar validaciones",
            unit_type="skill",
            unit_name="sandbox",
            params={
                "task": task,
            },
        )

        validate.depends_on.append(
            analyze.id,
        )

    # ======================================================
    # REFACTOR
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
        )

        modify = plan.add_step(
            description="Aplicar cambios",
            unit_type="agent",
            unit_name="coder",
            params={
                "task": task,
            },
        )

        modify.depends_on.append(
            analyze.id,
        )

    # ======================================================
    # DOCUMENTATION
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
    # FILE CREATION
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
    # COMMAND EXECUTION
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
    # DOCKER
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
    # DEFAULT
    # ======================================================

    @staticmethod
    def _plan_default(
        plan: ExecutionPlan,
        task: str,
    ) -> None:

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
