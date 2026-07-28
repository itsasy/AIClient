import json
import logging
import os

from core.config import Config
from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from core.engram_memory import EngramMemory
from core.learner import ContinuousLearner
from agents.manager import AgentManager
from agents.self_critic import SelfCriticAgent
from llm.intent_analyzer import IntentAnalyzer

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestador principal del sistema.

    Coordina el flujo completo:
    1. Análisis de intención
    2. Construcción de contexto (proyecto + Obsidian + Engram)
    3. Delegación al agente (genera respuesta)
    4. Auto-evaluación (Self-Critic) si está habilitada
    5. Aprendizaje continuo (detecta correcciones del usuario)
    6. Persistencia: memoria conversacional + Engram
    """

    def __init__(self):
        self.context_builder = ContextBuilder()
        self.memory = ConversationMemory()
        self.agent_manager = AgentManager()
        self.learner = ContinuousLearner()
        self.critic = SelfCriticAgent()
        self.engram = EngramMemory()

        logger.info("Orchestrator iniciado con Engram + Self-Critic")

    def process(self, task: str) -> str:
        """
        Procesa una tarea completa del usuario.
        """
        # ------------------------------------------------------------
        # 1. ANÁLISIS DE INTENCIÓN
        # ------------------------------------------------------------
        intent = IntentAnalyzer.analyze(task)
        logger.info(
            "Intención detectada | skill=%s | params=%s",
            intent.skill_name or "general",
            intent.skill_params or {},
        )

        # ------------------------------------------------------------
        # 2. CONSTRUCCIÓN DE CONTEXTO (Proyecto + Obsidian)
        # ------------------------------------------------------------
        context = self.context_builder.build(task)

        # ------------------------------------------------------------
        # 3. INYECCIÓN DE MEMORIA DE ENGRAM (persistente)
        # ------------------------------------------------------------
        engram_ctx = self.engram.get_context(task)
        if engram_ctx:
            context["engram"] = engram_ctx
            logger.info(
                "Contexto recuperado de Engram (%d caracteres)", len(engram_ctx)
            )

        # ------------------------------------------------------------
        # 4. INYECCIÓN DE MEMORIA CONVERSACIONAL (sesión actual)
        # ------------------------------------------------------------
        memory = self.memory.get_context()
        if memory:
            context["memory"] = memory

        # ------------------------------------------------------------
        # 5. DELEGACIÓN AL AGENTE (genera la respuesta)
        # ------------------------------------------------------------
        response = self.agent_manager.delegate(
            task=task,
            context=context,
            skill_name=intent.skill_name,
            skill_params=intent.skill_params,
        )

        # ------------------------------------------------------------
        # 6. SELF-CRITIC (auto-evaluación de la respuesta)
        # ------------------------------------------------------------
        if self._should_critic(task):
            eval_result = self.critic.process(task, context, response)
            if eval_result:
                # 6a. Guardar evaluación en Engram
                self.engram.save(
                    json.dumps(eval_result, ensure_ascii=False),
                    tags=[
                        "reflection",
                        "self_critic",
                        f"score_{eval_result.get('alignment_score', 0)}",
                        f"risk_{eval_result.get('hallucination_risk', 'unknown')}",
                    ],
                )
                logger.info(
                    "Self-Critic guardado | score=%s | risk=%s",
                    eval_result.get("alignment_score"),
                    eval_result.get("hallucination_risk"),
                )

                # 6b. Enriquecer la respuesta con el resumen del crítico
                summary = eval_result.get("summary", "Evaluación no disponible.")
                critic_footer = f"\n\n---\n🤖 **Self-Critic:** {summary}"

                if eval_result.get("hallucination_risk") == "high":
                    critic_footer += "\n⚠️ **Alerta:** Alto riesgo de alucinación. Verifica el contexto."
                elif eval_result.get("alignment_score", 0) < 5:
                    critic_footer += "\n⚠️ **Desviación detectada.** Revisa la recomendación de corrección."

                response = response + critic_footer

        # ------------------------------------------------------------
        # 7. APRENDIZAJE CONTINUO (detectar correcciones del usuario)
        # ------------------------------------------------------------
        if self.learner.extract_and_learn(task, response):
            logger.info("Nuevo estándar aprendido. Guardando también en Engram.")
            # Guardar el estándar aprendido también en Engram para trazabilidad
            self.engram.save(
                f"Estándar aprendido: {task[:200]}",
                tags=["learning", "standard", "continuous_learning"],
            )

        # ------------------------------------------------------------
        # 8. PERSISTENCIA EN ENGRAM (guardar la interacción completa)
        # ------------------------------------------------------------
        # Guardar la consulta del usuario
        self.engram.save(
            f"Usuario: {task}",
            tags=["user_query", "interaction", "raw"],
        )
        # Guardar la respuesta del asistente (acortada para no saturar)
        self.engram.save(
            f"Asistente: {response[:500]}",
            tags=["assistant_response", "interaction", "raw"],
        )

        # ------------------------------------------------------------
        # 9. PERSISTENCIA EN MEMORIA CONVERSACIONAL (.history.json)
        # ------------------------------------------------------------
        self.memory.add(task, response)

        # ------------------------------------------------------------
        # 10. DEVOLVER RESPUESTA AL USUARIO
        # ------------------------------------------------------------
        return response

    def _should_critic(self, task: str) -> bool:
        """
        Heurística para decidir si la tarea merece auto-evaluación.
        """
        # 1. Verificar si está habilitado globalmente
        if not getattr(Config, "ENABLE_SELF_CRITIC", True):
            return False

        # 2. Si la tarea es muy corta (< 5 palabras), no criticar
        words = task.split()
        if len(words) < 5:
            return False

        # 3. Palabras clave que activan el crítico
        keywords = [
            "plan",
            "planifica",
            "crea",
            "genera",
            "arquitectura",
            "diseño",
            "proyecto",
            "complejo",
            "especificación",
            "spec",
            "refactor",
            "migra",
            "estructura",
        ]
        return any(k in task.lower() for k in keywords)
