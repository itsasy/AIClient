import logging
import time

from agents.manager import AgentManager
from agents.self_critic import SelfCriticAgent

from core.context.base import ContextProvider
from core.engram_memory import EngramMemory
from core.learner import ContinuousLearner
from core.memory import ConversationMemory

from llm.intent_analyzer import IntentAnalyzer

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Núcleo del sistema.

    Flujo:

        User
          │
          ▼
    IntentAnalyzer
          │
          ▼
    ExecutionPlan
          │
          ▼
    ContextProvider
          │
          ▼
    AgentManager
          │
          ▼
    Agent
          │
          ▼
    LLMRouter
          │
          ▼
    Provider

    Luego:
        • Self Critic
        • Continuous Learning
        • Engram
        • Conversation Memory
    """

    def __init__(self):

        self.agent_manager = AgentManager()

        self.context_provider = ContextProvider()

        self.memory = ConversationMemory()

        self.engram = EngramMemory()

        self.learner = ContinuousLearner()

        self.critic = SelfCriticAgent()

        logger.info("Orchestrator inicializado.")

    def process(
        self,
        task: str,
        verbose: bool = False,
    ) -> str:

        start = time.time()

        # ==========================================================
        # 1. INTENT ANALYSIS
        # ==========================================================

        plan = IntentAnalyzer.analyze(task)

        logger.info(
            "ExecutionPlan | intent=%s | skill=%s | agent=%s",
            plan.intent,
            plan.skill,
            plan.agent,
        )

        # ==========================================================
        # 2. CONTEXT
        # ==========================================================

        context = self.context_provider.build(plan)

        logger.info(
            "Context providers cargados: %s",
            ", ".join(context.keys()),
        )

        # ==========================================================
        # 3. AGENTE
        # ==========================================================

        response = self.agent_manager.delegate(
            plan=plan,
            context=context,
        )

        # ==========================================================
        # 4. SELF CRITIC
        # ==========================================================

        if plan.requires_self_critic:

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
        # 5. CONTINUOUS LEARNING
        # ==========================================================

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
        # 6. ENGRAM
        # ==========================================================

        try:

            self.engram.save(
                plan.original_task,
                tags=[
                    "user",
                    plan.intent or "conversation",
                ],
            )

            self.engram.save(
                response,
                tags=[
                    "assistant",
                    plan.intent or "conversation",
                ],
            )

        except Exception:

            logger.exception("Error guardando en Engram.")

        # ==========================================================
        # 7. MEMORIA CONVERSACIONAL
        # ==========================================================

        try:

            self.memory.add(
                plan.original_task,
                response,
            )

        except Exception:

            logger.exception("ConversationMemory falló.")

        elapsed = time.time() - start

        logger.info(
            "Tiempo total %.2fs",
            elapsed,
        )

        if verbose:

            logger.info(
                "ExecutionPlan:\n%s",
                plan.to_dict(),
            )

        return response
