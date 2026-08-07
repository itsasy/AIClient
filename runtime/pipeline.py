from __future__ import annotations

import logging
import time

from typing import Any, Callable

from core.execution_result import ExecutionResult
from core.intent import IntentAnalyzer, IntentResult

from core.planning.plan_builder import PlanBuilder

from runtime.execution_engine import ExecutionEngine

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Fachada principal del sistema.

    Flujo:

        User Input
            |
            v
        IntentAnalyzer
            |
            v
        PlanBuilder
            |
            v
        ExecutionPlan
            |
            v
        ExecutionEngine
            |
            v
        ExecutionResult


    Responsabilidades:

    - Recibir input externo.
    - Analizar intención.
    - Crear ExecutionPlan.
    - Delegar ejecución.
    - Emitir eventos.

    No:

    - Ejecuta Agents.
    - Ejecuta Skills.
    - Construye contexto.
    - Gestiona memoria.
    - Gestiona aprendizaje.
    - Modifica resultados.
    """

    name = "pipeline"

    def __init__(
        self,
        intent_analyzer: IntentAnalyzer | None = None,
        plan_builder: PlanBuilder | None = None,
        execution_engine: ExecutionEngine | None = None,
    ):

        self.intent_analyzer = intent_analyzer or IntentAnalyzer()

        self.plan_builder = plan_builder or PlanBuilder()

        self.execution_engine = execution_engine or ExecutionEngine()

        self.listeners: dict[str, list[Callable]] = {}

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
            "duration": 0,
        }

    # ==================================================
    # Public API
    # ==================================================

    def run(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        start = time.time()

        metadata = metadata or {}

        self.metrics["executions"] += 1

        try:

            self.emit(
                "pipeline_started",
                {
                    "input": user_input,
                    "metadata": metadata,
                },
            )

            # ==========================================
            # Intent Analysis
            # ==========================================

            intent: IntentResult = self.intent_analyzer.analyze(
                user_input,
            )

            self.emit(
                "intent_detected",
                intent,
            )

            # ==========================================
            # Plan creation
            # ==========================================

            plan = self.plan_builder.build(
                intent=intent,
                original_task=user_input,
            )

            plan.metadata.update(
                {
                    "pipeline_metadata": metadata,
                }
            )

            self.emit(
                "plan_created",
                plan,
            )

            # ==========================================
            # Execution
            # ==========================================

            result = self.execution_engine.execute(
                plan,
            )

            duration = round(
                time.time() - start,
                3,
            )

            result.metadata.update(
                {
                    "pipeline": self.name,
                    "duration": duration,
                    "intent": intent.intent,
                }
            )

            self.metrics["duration"] += duration

            # ==========================================
            # Result lifecycle
            # ==========================================

            if result.status == "completed":

                self.metrics["success"] += 1

                self.emit(
                    "pipeline_completed",
                    result,
                )

            elif result.status == "partial":

                self.metrics["success"] += 1

                self.emit(
                    "pipeline_partial",
                    result,
                )

            else:

                self.metrics["failed"] += 1

                self.emit(
                    "pipeline_failed",
                    result,
                )

            return result

        except Exception as exc:

            duration = round(
                time.time() - start,
                3,
            )

            self.metrics["failed"] += 1

            logger.exception(
                "Pipeline error",
            )

            result = ExecutionResult.fail(
                error=str(exc),
                executor=self.name,
            )

            result.metadata.update(
                {
                    "pipeline": self.name,
                    "duration": duration,
                }
            )

            self.emit(
                "pipeline_error",
                result,
            )

            return result

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
                    "Error listener=%s",
                    event,
                )

    # ==================================================
    # Metrics
    # ==================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
