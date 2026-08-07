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
    Motor principal del sistema de ejecución.

    Responsabilidades:

    - Validar ExecutionPlan.
    - Construir contexto.
    - Gestionar lifecycle del plan.
    - Delegar ejecución.
    - Registrar métricas.
    - Emitir eventos.

    No:

    - Crea planes.
    - Analiza intención.
    - Ejecuta Agents.
    - Ejecuta Skills.
    - Gestiona memoria.
    - Gestiona aprendizaje.
    """

    name = "execution_engine"

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        execution_runtime: ExecutionRuntime | None = None,
    ) -> None:

        self.context_manager = context_manager or ContextManager()

        self.execution_runtime = execution_runtime or ExecutionRuntime()

        self.listeners: dict[str, list[Callable]] = {}

        self.metrics = {
            "executions": 0,
            "success": 0,
            "partial": 0,
            "failed": 0,
            "duration": 0,
            "context_duration": 0,
            "execution_duration": 0,
        }

    # ==================================================
    # Public API
    # ==================================================

    def execute(
        self,
        plan: ExecutionPlan,
    ) -> ExecutionResult:

        started = time.monotonic()

        self.metrics["executions"] += 1

        try:

            self._validate_plan(
                plan,
            )

            plan.mark_validated()

            self.emit(
                "plan_validated",
                plan,
            )

            plan.mark_running()

            self.emit(
                "execution_started",
                plan,
            )

            context_started = time.monotonic()

            context = (
                self.context_manager.build(
                    plan,
                )
                or {}
            )

            context_duration = round(
                time.monotonic() - context_started,
                3,
            )

            self.metrics["context_duration"] += context_duration

            self.emit(
                "context_ready",
                {
                    "plan_id": plan.id,
                    "plan": plan,
                    "duration": context_duration,
                },
            )

            execution_started = time.monotonic()

            result = self.execution_runtime.execute(
                plan,
                context,
            )

            execution_duration = round(
                time.monotonic() - execution_started,
                3,
            )

            duration = round(
                time.monotonic() - started,
                3,
            )

            self.metrics["duration"] += duration

            self.metrics["execution_duration"] += execution_duration

            result.metadata.update(
                {
                    "engine": self.name,
                    "plan_id": plan.id,
                    "duration": duration,
                    "context_duration": context_duration,
                    "execution_duration": execution_duration,
                }
            )

            self._apply_result_lifecycle(
                plan,
                result,
            )

            return result

        except Exception as exc:

            duration = round(
                time.monotonic() - started,
                3,
            )

            logger.exception(
                "Error en ExecutionEngine",
            )

            self.metrics["failed"] += 1

            try:

                plan.mark_failed(
                    str(exc),
                )

            except Exception:

                logger.exception(
                    "No se pudo actualizar estado del plan",
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

    # ==================================================
    # Lifecycle
    # ==================================================

    def _apply_result_lifecycle(
        self,
        plan: ExecutionPlan,
        result: ExecutionResult,
    ) -> None:

        if result.status == "completed":

            plan.mark_completed(
                result.output,
            )

            self.metrics["success"] += 1

            self.emit(
                "execution_completed",
                result,
            )

            return

        if result.status == "partial":

            plan.mark_partial(
                result=result.output,
                error=result.error,
            )

            self.metrics["partial"] += 1

            self.emit(
                "execution_partial",
                result,
            )

            return

        plan.mark_failed(
            result.error or "Error desconocido",
        )

        self.metrics["failed"] += 1

        self.emit(
            "execution_failed",
            result,
        )

    # ==================================================
    # Validation
    # ==================================================

    def _validate_plan(
        self,
        plan: ExecutionPlan,
    ) -> None:

        if not isinstance(
            plan,
            ExecutionPlan,
        ):

            raise TypeError(
                "ExecutionEngine requiere ExecutionPlan",
            )

        errors = plan.validate()

        if errors:

            raise ValueError("ExecutionPlan inválido: " + ", ".join(errors))

    # ==================================================
    # Events
    # ==================================================

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

                callback(
                    payload,
                )

            except Exception:

                logger.exception(
                    "Error en listener=%s",
                    event,
                )

    # ==================================================
    # Metrics
    # ==================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
