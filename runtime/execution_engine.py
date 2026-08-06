from __future__ import annotations

import logging
import time
from typing import Any

from core.context.manager import ContextManager
from core.execution_plan import ExecutionPlan
from core.execution_result import ExecutionResult

from runtime.execution_runtime import ExecutionRuntime

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """
    Motor principal del sistema.

    Responsabilidades:

    - Validar ExecutionPlan.
    - Preparar contexto.
    - Gestionar lifecycle global.
    - Delegar ejecución.
    - Registrar métricas.

    No:

    - Analiza intención.
    - Crea planes.
    - Ejecuta agentes.
    - Ejecuta skills.
    """

    name = "execution_engine"

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        execution_runtime: ExecutionRuntime | None = None,
    ):

        self.context_manager = context_manager or ContextManager()

        self.execution_runtime = execution_runtime or ExecutionRuntime()

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
            "duration": 0,
        }

    # ======================================================
    # Public API
    # ======================================================

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        start = time.time()

        self.metrics["executions"] += 1

        logger.info(
            "Inicio ejecución plan=%s",
            plan.id,
        )

        try:

            self._validate_plan(
                plan,
            )

            plan.mark_running()

            context = self.context_manager.build(
                plan,
            )

            result = self.execution_runtime.execute(
                plan,
                context,
            )

            duration = round(
                time.time() - start,
                3,
            )

            result.metadata.update(
                {
                    "duration": duration,
                    "engine": self.name,
                }
            )

            self.metrics["duration"] += duration

            if result.success:

                plan.mark_completed(
                    result.output,
                )

                self.metrics["success"] += 1

            else:

                plan.mark_failed(
                    result.error or "Error desconocido",
                )

                self.metrics["failed"] += 1

            return result

        except Exception as exc:

            duration = round(
                time.time() - start,
                3,
            )

            self.metrics["failed"] += 1

            plan.mark_failed(
                str(exc),
            )

            logger.exception(
                "Fallo ExecutionEngine plan=%s",
                plan.id,
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=self.name,
                plan_id=plan.id,
            )

    # ======================================================
    # Validation
    # ======================================================

    def _validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> None:

        errors = plan.validate()

        if errors:

            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

    # ======================================================
    # Metrics
    # ======================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
