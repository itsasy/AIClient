from __future__ import annotations

import logging
from typing import Any

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ExecutionPlanner:
    """
    Construye planes de ejecución a partir de una intención
    y contexto disponible.

    Responsabilidades:

    - Convertir Intent -> ExecutionPlan.
    - Seleccionar estrategia inicial.
    - Definir agente.
    - Definir skills.
    - Definir modo de ejecución.
    - Preparar parámetros.

    No:

    - Ejecuta skills.
    - Llama LLM.
    - Recupera memoria.
    - Ejecuta agentes.
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

        plan.execution_mode = "multi_step" if complexity in ("high", "complex") else "single"

        logger.info(
            "Creando ExecutionPlan | intent=%s domain=%s complexity=%s",
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

    # ==========================================================
    # PROJECT CREATION
    # ==========================================================

    @staticmethod
    def _plan_project_creation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Crear un nuevo proyecto de software"

        plan.agent = "architect"

        plan.add_skill(
            "analyze_project",
        )

        plan.execution_mode = "multi_step"

        plan.params = {
            "task": task,
        }

    # ==========================================================
    # CODE GENERATION
    # ==========================================================

    @staticmethod
    def _plan_code_generation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Generar código"

        plan.agent = "coder"

        plan.add_skill(
            "generate",
        )

        plan.params = {
            "task": task,
        }

    # ==========================================================
    # DEBUG
    # ==========================================================

    @staticmethod
    def _plan_debug(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Analizar y resolver problema técnico"

        plan.agent = "coder"

        plan.add_skill(
            "analyze",
        )

        plan.add_skill(
            "sandbox",
        )

        plan.execution_mode = "multi_step"

        plan.params = {
            "task": task,
        }

    # ==========================================================
    # REFACTOR
    # ==========================================================

    @staticmethod
    def _plan_refactor(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Refactorizar código existente"

        plan.agent = "architect"

        plan.add_skill(
            "analyze",
        )

        plan.add_skill(
            "generate",
        )

        plan.execution_mode = "multi_step"

        plan.params = {
            "task": task,
        }

    # ==========================================================
    # DOCUMENTATION
    # ==========================================================

    @staticmethod
    def _plan_documentation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Crear documentación"

        plan.agent = "writer"

        plan.add_skill(
            "readme",
        )

    # ==========================================================
    # FILE CREATION
    # ==========================================================

    @staticmethod
    def _plan_file_creation(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Crear archivo"

        plan.agent = "executor"

        plan.add_skill(
            "write_file",
        )

        plan.params = {
            "task": task,
        }

    # ==========================================================
    # COMMAND EXECUTION
    # ==========================================================

    @staticmethod
    def _plan_command_execution(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Ejecutar comando"

        plan.agent = "executor"

        plan.add_skill(
            "shell",
        )

        plan.params = {
            "task": task,
        }

    # ==========================================================
    # DOCKER
    # ==========================================================

    @staticmethod
    def _plan_docker(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.objective = "Operación Docker"

        plan.agent = "executor"

        plan.add_skill(
            "sandbox",
        )

        plan.params = {
            "task": task,
        }

    # ==========================================================
    # DEFAULT
    # ==========================================================

    @staticmethod
    def _plan_default(
        plan: ExecutionPlan,
        task: str,
        context: dict[str, Any],
    ):

        plan.intent = "conversation"

        plan.objective = task

        plan.agent = "task"

        plan.add_skill(
            "conversation",
        )

    # ==========================================================
    # CONTEXT
    # ==========================================================

    @staticmethod
    def _apply_context_requirements(
        plan: ExecutionPlan,
        context: dict[str, Any],
    ):

        available = set(
            context.keys(),
        )

        for item in [
            "project",
            "memory",
            "engram",
            "documents",
            "standards",
            "knowledge",
            "gentleman",
        ]:

            if item in available:

                plan.add_context_requirement(
                    item,
                )
