from __future__ import annotations

import logging
from typing import Any

from core.context.manager import ContextManager
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult
from runtime.execution_runtime import ExecutionRuntime

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Motor principal de ejecución.

    Flujo:

    ExecutionPlan
          |
          v
    ContextManager
          |
          v
    ExecutionRuntime
          |
          v
    Agent / Skill
          |
          v
       Result


    Responsabilidades:

    - Ejecutar ExecutionPlans completos.
    - Construir contexto.
    - Delegar ejecución al runtime unificado.
    - Gestionar lifecycle general.

    No:

    - Analiza intención.
    - Crea ExecutionPlans.
    - Selecciona LLM.
    - Ejecuta Agents directamente.
    - Ejecuta Skills directamente.
    """

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        execution_runtime: ExecutionRuntime | None = None,
    ):

        self.context_manager = context_manager or ContextManager()

        self.execution_runtime = execution_runtime or ExecutionRuntime()

        self.metrics = {
            "executions": 0,
            "failed": 0,
        }

    # ==========================================================
    # Execution
    # ==========================================================

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> Any:

        logger.info(
            "Inicio ejecución plan=%s",
            plan.id,
        )

        self.metrics["executions"] += 1

        try:

            errors = plan.validate()

            if errors:

                logger.warning(
                    "ExecutionPlan inválido errors=%s",
                    errors,
                )

            context = self.context_manager.build(
                plan,
            )

            result = self.execution_runtime.execute(plan, context)

            return result

        except Exception as exc:

            self.metrics["failed"] += 1

            logger.exception(
                "ExecutionEngine fallo plan=%s",
                plan.id,
            )

            plan.mark_failed(
                str(exc),
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor="execution_engine",
                plan_id=plan.id,
            )

    # ==========================================================
    # Information
    # ==========================================================

    def get_metrics(
        self,
    ) -> dict:

        return self.metrics.copy()
