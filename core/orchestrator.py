from __future__ import annotations

import logging
import time

from agents.manager import AgentManager
from agents.self_critic import SelfCriticAgent

from core.context.manager import ContextManager
from core.engram_memory import EngramMemory
from core.execution_plan import ExecutionPlan
from core.intent_analyzer import IntentAnalyzer
from core.learner import ContinuousLearner
from core.memory import ConversationMemory

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestador principal del sistema.

    Flujo:

        User
          |
          v
    IntentAnalyzer
          |
          v
    ExecutionPlan
          |
          v
    ContextManager
          |
          v
    AgentManager
          |
          v
    LLMRouter
          |
          v
    Provider


    Post ejecución:

        - Self Critic
        - Continuous Learning
        - Engram
        - Conversation Memory
    """

    def __init__(self):

        self.agent_manager = AgentManager()

        self.context_manager = ContextManager()

        self.memory = ConversationMemory()

        self.engram = EngramMemory()

        self.learner = ContinuousLearner()

        self.critic = SelfCriticAgent()

        logger.info("Orchestrator inicializado.")

    # ==========================================================
    # Public API
    # ==========================================================

    def process(
        self,
        task: str,
        verbose: bool = False,
    ) -> str:

        start = time.time()

        plan: ExecutionPlan | None = None

        try:

            # ==================================================
            # 1. INTENT ANALYSIS
            # ==================================================

            plan = IntentAnalyzer.analyze(
                task,
            )

            validation_errors = plan.validate()

            if validation_errors:

                logger.warning(
                    "ExecutionPlan inválido: %s",
                    validation_errors,
                )

            logger.info(
                "ExecutionPlan | intent=%s | skill=%s | agent=%s",
                plan.intent,
                plan.primary_skill(),
                plan.agent,
            )

            # ==================================================
            # 2. CONTEXT BUILDING
            # ==================================================

            context = self.context_manager.build(
                plan,
            )

            logger.info(
                "Context providers cargados: %s",
                list(context.keys()),
            )

            # ==================================================
            # 3. EXECUTION
            # ==================================================

            plan.status = "running"

            response = self.agent_manager.delegate(
                plan=plan,
                context=context,
            )

            plan.status = "completed"

            plan.metrics["execution_time"] = time.time() - start

            # ==================================================
            # 4. POST PROCESSING
            # ==================================================

            self._run_post_processing(
                plan,
                context,
                response,
            )

            elapsed = time.time() - start

            logger.info(
                "Ejecución completada en %.2fs",
                elapsed,
            )

            if verbose:

                logger.info(
                    "ExecutionPlan:\n%s",
                    plan.to_dict(),
                )

            return response

        except Exception as exc:

            logger.exception("Error procesando tarea.")

            if plan:

                plan.status = "failed"

                plan.metrics["error"] = str(exc)

            raise

    # ==========================================================
    # POST PROCESSING
    # ==========================================================

    def _run_post_processing(
        self,
        plan: ExecutionPlan,
        context: dict,
        response: str,
    ) -> None:

        self._run_self_critic(
            plan,
            context,
            response,
        )

        self._run_learning(
            plan,
            response,
        )

        self._save_engram(
            plan,
            response,
        )

        self._save_memory(
            plan,
            response,
        )

    # ==========================================================
    # SELF CRITIC
    # ==========================================================

    def _run_self_critic(
        self,
        plan: ExecutionPlan,
        context: dict,
        response: str,
    ) -> None:

        if not plan.requires_self_critic:

            return

        try:

            evaluation = self.critic.process(
                task=plan.original_task,
                context=context,
                draft_response=response,
            )

            if evaluation:

                self.engram.save(
                    str(evaluation),
                    tags=[
                        "self_critic",
                        "reflection",
                    ],
                )

        except Exception:

            logger.exception("SelfCritic falló.")

    # ==========================================================
    # LEARNING
    # ==========================================================

    def _run_learning(
        self,
        plan: ExecutionPlan,
        response: str,
    ) -> None:

        try:

            learned = self.learner.extract_and_learn(
                plan.original_task,
                response,
            )

            if learned:

                self.engram.save(
                    learned,
                    tags=[
                        "learning",
                        "standard",
                    ],
                )

        except Exception:

            logger.exception("ContinuousLearner falló.")

    # ==========================================================
    # ENGRAM
    # ==========================================================

    def _save_engram(
        self,
        plan: ExecutionPlan,
        response: str,
    ) -> None:

        try:

            intent = plan.intent or "conversation"

            self.engram.save(
                plan.original_task,
                tags=[
                    "user",
                    intent,
                ],
            )

            self.engram.save(
                response,
                tags=[
                    "assistant",
                    intent,
                ],
            )

        except Exception:

            logger.exception("Error guardando en Engram.")

    # ==========================================================
    # MEMORY
    # ==========================================================

    def _save_memory(
        self,
        plan: ExecutionPlan,
        response: str,
    ) -> None:

        try:

            self.memory.add(
                plan.original_task,
                response,
            )

        except Exception:

            logger.exception("ConversationMemory falló.")
