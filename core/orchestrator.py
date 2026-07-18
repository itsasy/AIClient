import logging

from agents.manager import AgentManager
from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from llm.intent_analyzer import IntentAnalyzer
from core.learner import ContinuousLearner

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestador principal del sistema.

    Coordina el flujo completo: análisis de intención, construcción de contexto,
    recuperación de memoria, delegación al agente y almacenamiento de la respuesta.

    Atributos:
        context_builder (ContextBuilder): Construye el contexto del proyecto y Obsidian.
        memory (ConversationMemory): Gestiona el historial conversacional.
        agent_manager (AgentManager): Selecciona y delega tareas a los agentes.
    """

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()
        self.agent_manager = AgentManager()
        self.learner = ContinuousLearner()

    def process(self, task: str) -> str:
        """
        Procesa una tarea completa del usuario.

        Args:
            task (str): Instrucción o consulta del usuario.

        Returns:
            str: Respuesta generada por el agente/LLM.
        """
        intent = IntentAnalyzer.analyze(task)

        logger.info(
            "Intención detectada | skill=%s | params=%s",
            intent.skill_name or "general",
            intent.skill_params or {},
        )

        context = self.context_builder.build(task)

        memory = self.memory.get_context()
        if memory:
            context["memory"] = memory

        if self.learner.extract_and_learn(task, response):
            logger.info("El sistema ha aprendido una nueva preferencia del usuario.")

        response = self.agent_manager.delegate(
            task=task,
            context=context,
            skill_name=intent.skill_name,
            skill_params=intent.skill_params,
        )

        self.memory.add(task, response)

        return response
