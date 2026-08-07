from __future__ import annotations

import logging
import time

from typing import Any, Callable

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
    - Gestionar lifecycle global.
    - Construir contexto.
    - Delegar ejecución.
    - Emitir eventos.
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

        self.listeners: dict[str, list[Callable]] = {}

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
            "critical_errors": 0,
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

        self.emit(
            "execution_started",
            {
                "plan": plan,
                "plan_id": plan.id,
            },
        )

        try:

            self._validate_plan(plan)

            plan.mark_running()

            self.emit(
                "plan_running",
                plan,
            )

            context_start = time.time()

            context = self.context_manager.build(
                plan,
            )

            if context is None:

                context = {}

            context_duration = round(
                time.time() - context_start,
                3,
            )

            self.emit(
                "context_ready",
                {
                    "plan_id": plan.id,
                    "duration": context_duration,
                },
            )

            execution_start = time.time()

            result = self.execution_runtime.execute(
                plan,
                context,
            )

            execution_duration = round(
                time.time() - execution_start,
                3,
            )

            duration = round(
                time.time() - start,
                3,
            )

            result.metadata.update(
                {
                    "engine": self.name,
                    "duration": duration,
                    "context_duration": context_duration,
                    "execution_duration": execution_duration,
                }
            )

            self.metrics["duration"] += duration

            if result.success:

                plan.mark_completed(
                    result.output,
                )

                self.metrics["success"] += 1

                self.emit(
                    "execution_completed",
                    result,
                )

            else:

                plan.mark_failed(
                    result.error or "Error desconocido",
                )

                self.metrics["failed"] += 1

                self.emit(
                    "execution_failed",
                    result,
                )

            return result

        except Exception as exc:

            duration = round(
                time.time() - start,
                3,
            )

            self.metrics["failed"] += 1
            self.metrics["critical_errors"] += 1

            try:

                plan.mark_failed(
                    str(exc),
                )

            except Exception:

                logger.exception(
                    "No se pudo actualizar lifecycle del plan",
                )

            logger.exception(
                "Error crítico ExecutionEngine",
            )

            result = ExecutionResult.fail(
                error=str(exc),
                executor=self.name,
                plan_id=getattr(
                    plan,
                    "id",
                    None,
                ),
            )

            result.metadata.update(
                {
                    "engine": self.name,
                    "duration": duration,
                }
            )

            self.emit(
                "engine_error",
                result,
            )

            return result

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
    # Events
    # ======================================================

    def on(
        self,
        event: str,
        callback: Callable,
    ) -> None:

        self.listeners.setdefault(
            event,
            [],
        ).append(
            callback,
        )

    def emit(
        self,
        event: str,
        payload: Any,
    ) -> None:

        for callback in self.listeners.get(
            event,
            [],
        ):

            try:

                callback(payload)

            except Exception:

                logger.exception(
                    "Error listener=%s",
                    event,
                )

    # ======================================================
    # Metrics
    # ======================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
