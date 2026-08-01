import logging
import time

from llm.intent_analyzer import IntentAnalyzer

from core.execution_plan import ExecutionPlan
from core.context.provider import ContextProvider

from agents.manager import AgentManager

from core.memory import ConversationMemory
from core.engram_memory import EngramMemory
from core.learner import ContinuousLearner

from agents.self_critic import SelfCriticAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestador principal.

    Responsabilidades:
    - Analizar intención
    - Crear ExecutionPlan
    - Construir contexto
    - Delegar ejecución
    - Persistir aprendizaje

    No ejecuta skills.
    No construye prompts.
    No decide proveedores LLM.
    """

    def __init__(self):

        self.agent_manager = AgentManager()

        self.context_provider = ContextProvider()

        self.memory = ConversationMemory()

        self.engram = EngramMemory()

        self.learner = ContinuousLearner()

        self.critic = SelfCriticAgent()

        logger.info("Orchestrator inicializado con ExecutionPlan + ContextProviders")

    def process(
        self,
        task: str,
        verbose: bool = False,
    ) -> str:

        start = time.time()

        # ==================================================
        # 1. INTENT ANALYSIS
        # ==================================================

        intent = IntentAnalyzer.analyze(task)

        logger.info("Intent detectado: %s", intent.skill_name)

        # ==================================================
        # 2. CREAR EXECUTION PLAN
        # ==================================================

        plan = ExecutionPlan.from_intent(
            task=task,
            intent=intent,
        )

        logger.info("ExecutionPlan creado: %s", plan)

        # ==================================================
        # 3. CONTEXT BUILDING
        # ==================================================

        context = self.context_provider.build(plan)

        logger.info("Context providers ejecutados")

        # ==================================================
        # 4. EJECUCIÓN DEL AGENTE
        # ==================================================

        response = self.agent_manager.delegate(
            plan=plan,
            context=context,
        )

        # ==================================================
        # 5. SELF CRITIC
        # ==================================================

        if plan.requires_review:

            evaluation = self.critic.process(
                task,
                context,
                response,
            )

            if evaluation:

                self.engram.save(
                    str(evaluation),
                    tags=[
                        "reflection",
                        "self_critic",
                    ],
                )

        # ==================================================
        # 6. APRENDIZAJE
        # ==================================================

        learned = self.learner.extract_and_learn(task, response)

        if learned:

            self.engram.save(
                f"Nuevo estándar aprendido: {task[:200]}",
                tags=[
                    "learning",
                    "standard",
                ],
            )

        # ==================================================
        # 7. MEMORIA
        # ==================================================

        self.engram.save(
            f"Usuario: {task}",
            tags=[
                "interaction",
                "user",
            ],
        )

        self.engram.save(
            f"Asistente: {response[:500]}",
            tags=[
                "interaction",
                "assistant",
            ],
        )

        self.memory.add(task, response)

        logger.info("Tiempo total: %.3fs", time.time() - start)

        return response
