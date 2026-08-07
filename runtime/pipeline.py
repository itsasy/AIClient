from __future__ import annotations

import logging
import time

from typing import Any, Callable

from core.execution_planner import ExecutionPlanner
from core.execution_result import ExecutionResult

from runtime.execution_engine import ExecutionEngine

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Fachada principal del sistema.

    Flujo:

    User Input
        |
        v
    Intent Analyzer
        |
        v
    Execution Planner
        |
        v
    Execution Engine
        |
        v
    Execution Result


    Responsabilidades:

    - Recibir input externo.
    - Resolver intención.
    - Crear ExecutionPlan.
    - Delegar ejecución.
    - Gestionar aprendizaje externo.
    - Emitir eventos.
    - Registrar métricas globales.


    No:

    - Ejecuta agentes.
    - Ejecuta skills.
    - Construye contexto.
    - Valida planes.
    """

    name = "pipeline"

    def __init__(
        self,
        intent_analyzer=None,
        planner: ExecutionPlanner | None = None,
        execution_engine: ExecutionEngine | None = None,
        learner=None,
    ):

        self.intent_analyzer = intent_analyzer

        self.planner = planner or ExecutionPlanner()

        self.execution_engine = execution_engine or ExecutionEngine()

        self.learner = learner

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

    def run(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        start = time.time()

        metadata = metadata or {}

        self.metrics["executions"] += 1

        self.emit(
            "pipeline_started",
            {
                "input": user_input,
                "metadata": metadata,
            },
        )

        try:

            logger.info(
                "Pipeline iniciado input=%s",
                user_input[:100],
            )

            intent = self._analyze_intent(
                user_input,
                metadata,
            )

            self.emit(
                "intent_ready",
                intent,
            )

            plan = self.planner.create(
                task=user_input,
                intent=intent,
                context=metadata,
            )

            self.emit(
                "plan_created",
                plan,
            )

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
                    "pipeline_duration": duration,
                }
            )

            self.metrics["duration"] += duration

            self._learn(
                user_input,
                result,
            )

            if result.success:

                self.metrics["success"] += 1

                self.emit(
                    "pipeline_completed",
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
            self.metrics["critical_errors"] += 1
            self.metrics["duration"] += duration

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
                    "pipeline_duration": duration,
                    "pipeline_error": True,
                }
            )

            self.emit(
                "pipeline_error",
                result,
            )

            return result

    # ======================================================
    # Intent
    # ======================================================

    def _analyze_intent(
        self,
        task: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:

        existing_intent = metadata.get(
            "intent",
        )

        if existing_intent:

            return existing_intent

        if self.intent_analyzer:

            return self.intent_analyzer.analyze(
                task,
            )

        return {
            "intent": "conversation",
            "domain": "general",
            "complexity": "normal",
        }

    # ======================================================
    # Learning
    # ======================================================

    def _learn(
        self,
        query: str,
        result: ExecutionResult,
    ) -> None:

        if not self.learner:

            return

        try:

            self.learner.extract_and_learn(
                query,
                result.to_dict(),
            )

        except Exception:

            logger.exception(
                "Error aprendizaje continuo",
            )

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

                callback(
                    payload,
                )

            except Exception:

                logger.exception(
                    "Error listener pipeline=%s",
                    event,
                )

    # ======================================================
    # Metrics
    # ======================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
