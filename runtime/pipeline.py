from __future__ import annotations

import logging
from typing import Any

from core.execution_planner import ExecutionPlanner
from core.context.manager import ContextManager

from runtime.execution_engine import ExecutionEngine

logger = logging.getLogger(__name__)


class Pipeline:
    """
    Orquestador principal del flujo de ejecución.

    Flujo:

    User Input
        |
        v
    Intent
        |
        v
    ExecutionPlanner
        |
        v
    ExecutionPlan
        |
        v
    ContextManager
        |
        v
    ExecutionEngine
        |
        v
    Result


    Responsabilidades:

    - Coordinar componentes.
    - Mantener ciclo de vida de una tarea.
    - Centralizar métricas.


    No:

    - Analiza intención internamente.
    - Ejecuta agentes.
    - Ejecuta skills.
    - Genera prompts.
    """

    def __init__(
        self,
        intent_analyzer=None,
        planner=None,
        context_manager=None,
        execution_engine=None,
        learner=None,
    ):

        self.intent_analyzer = intent_analyzer

        self.planner = planner or ExecutionPlanner

        self.context_manager = context_manager or ContextManager()

        self.execution_engine = execution_engine or ExecutionEngine()

        self.learner = learner

        self.metrics = {
            "executions": 0,
            "success": 0,
            "failed": 0,
        }

    # ==========================================================
    # Public API
    # ==========================================================

    def run(
        self,
        user_input: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:

        metadata = metadata or {}

        self.metrics["executions"] += 1

        try:

            logger.info(
                "Pipeline iniciado | task=%s",
                user_input[:100],
            )

            # --------------------------------------------------
            # 1. Intent Understanding
            # --------------------------------------------------

            intent = self._understand_intent(
                user_input,
                metadata,
            )

            # --------------------------------------------------
            # 2. Execution Planning
            # --------------------------------------------------

            plan = self.planner.create(
                task=user_input,
                intent=intent,
                context=metadata,
            )

            logger.info(
                "Plan creado: %s",
                plan,
            )

            errors = plan.validate()

            if errors:

                logger.warning(
                    "ExecutionPlan con advertencias: %s",
                    errors,
                )

            # --------------------------------------------------
            # 3. Execution
            # --------------------------------------------------

            result = self.execution_engine.execute(plan)

            # --------------------------------------------------
            # 4. Learning
            # --------------------------------------------------

            self._learn(
                user_input,
                result,
            )

            if getattr(result, "success", False):
                self.metrics["success"] += 1
            else:
                self.metrics["failed"] += 1

            return result

        except Exception as exc:

            self.metrics["failed"] += 1

            logger.exception(
                "Error en Pipeline: %s",
                exc,
            )

            raise

    # ==========================================================
    # Intent
    # ==========================================================

    def _understand_intent(
        self,
        task: str,
        metadata: dict,
    ) -> dict[str, Any]:
        """
        Actualmente permite inyectar
        un analizador externo.

        Luego conectará:

        IntentClassifier
        LLM Router
        Rules Engine
        """

        if self.intent_analyzer:

            return self.intent_analyzer.analyze(
                task,
            )

        # fallback temporal

        return {
            "intent": "conversation",
            "domain": "general",
            "complexity": "normal",
        }

    # ==========================================================
    # Learning
    # ==========================================================

    def _learn(
        self,
        query: str,
        result: Any,
    ):

        if not self.learner:

            return

        try:

            self.learner.extract_and_learn(
                query,
                str(result),
            )

        except Exception:

            logger.exception(
                "Error en aprendizaje continuo",
            )

    # ==========================================================
    # Metrics
    # ==========================================================

    def get_metrics(
        self,
    ) -> dict:

        return self.metrics.copy()
