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
    - Analizar intención → ExecutionPlan
    - Construir contexto bajo demanda
    - Delegar ejecución al agente
    - Persistir aprendizaje y memoria

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

        logger.info("Orchestrator inicializado con ExecutionPlan + ContextProvider")

    def process(self, task: str, verbose: bool = False) -> str:
        start = time.time()

        # ==================================================
        # 1. INTENT ANALYSIS → ExecutionPlan
        # ==================================================
        plan = IntentAnalyzer.analyze(task) 
        logger.info(
            "Plan creado: intent=%s, skill=%s, agent=%s", plan.intent, plan.skill, plan.agent
        )

        # ==================================================
        # 2. CONTEXT BUILDING (bajo demanda)
        # ==================================================
        context = self.context_provider.build(plan)
        logger.info("Contexto construido (requerimientos: %s)", plan.context_requirements)

        # ==================================================
        # 3. DELEGACIÓN AL AGENTE
        # ==================================================
        response = self.agent_manager.delegate(
            plan=plan,
            context=context,
        )

        # ==================================================
        # 4. SELF-CRITIC (solo si el plan lo requiere)
        # ==================================================
        if plan.requires_self_critic:  # ✅ CORREGIDO
            try:
                evaluation = self.critic.process(
                    plan.original_task,  # ✅ usar plan.original_task
                    context,
                    response,
                )
                if evaluation:
                    self.engram.save(
                        str(evaluation),
                        tags=["reflection", "self_critic"],
                    )
                    logger.info("Self-Critic ejecutado")
            except Exception as e:
                logger.warning("Self-Critic falló: %s", e)

        # ==================================================
        # 5. APRENDIZAJE CONTINUO
        # ==================================================
        learned = self.learner.extract_and_learn(plan.original_task, response)
        if learned:
            self.engram.save(
                f"Nuevo estándar aprendido: {plan.original_task[:200]}",
                tags=["learning", "standard"],
            )
            logger.info("Nuevo estándar aprendido")

        # ==================================================
        # 6. PERSISTENCIA (Engram + Memoria conversacional)
        # ==================================================
        self.engram.save(
            f"Usuario: {plan.original_task}",
            tags=["interaction", "user"],
        )
        self.engram.save(
            f"Asistente: {response[:500]}",
            tags=["interaction", "assistant"],
        )
        self.memory.add(plan.original_task, response)

        logger.info("Tiempo total: %.3fs", time.time() - start)
        return response
