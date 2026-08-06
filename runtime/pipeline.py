from __future__ import annotations

import logging
from typing import Any


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


    Responsabilidad:

    - Coordinar componentes superiores.
    - Exponer API simple.
    - Gestionar métricas globales.


    No:

    - Ejecuta agentes.
    - Ejecuta skills.
    - Valida planes.
    - Construye contexto.
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

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
        }

    # ======================================================
    # Public API
    # ======================================================

    def run(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> ExecutionResult:

        metadata = metadata or {}

        self.metrics["executions"] += 1

        try:

            logger.info(
                "Pipeline iniciado: %s",
                user_input[:100],
            )

            intent = self._analyze_intent(
                user_input,
                metadata,
            )

            plan = self.planner.create(
                task=user_input,
                intent=intent,
                context=metadata,
            )

            result = self.execution_engine.execute(
                plan,
            )

            self._learn(
                user_input,
                result,
            )

            if result.success:

                self.metrics["success"] += 1

            else:

                self.metrics["failed"] += 1

            return result

        except Exception as exc:

            self.metrics["failed"] += 1

            logger.exception(
                "Pipeline error",
            )

            return ExecutionResult.fail(
                error=str(exc),
                executor=self.name,
            )

    # ======================================================
    # Intent
    # ======================================================

    def _analyze_intent(
        self,
        task: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:

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
    # Metrics
    # ======================================================

    def get_metrics(
        self,
    ) -> dict[str, Any]:

        return self.metrics.copy()
