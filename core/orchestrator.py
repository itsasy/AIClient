import json
import logging
from typing import Optional

from core.config import Config
from core.context_builder import ContextBuilder
from core.memory import ConversationMemory
from core.engram_memory import EngramMemory
from core.learner import ContinuousLearner
from core.spec_manager import SpecManager
from agents.manager import AgentManager
from agents.self_critic import SelfCriticAgent
from llm.intent_analyzer import IntentAnalyzer

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Orquestador principal del sistema.

    Coordina el flujo completo:
    1. Análisis de intención
    2. Construcción de contexto (proyecto + Obsidian + Engram + Specs)
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
        self.spec_manager = SpecManager()

        logger.info("Orchestrator iniciado con Engram + Self-Critic + SpecManager")

    def process(self, task: str, verbose: bool = False) -> str:
        """
        Procesa una tarea completa del usuario.
        """

        # ------------------------------------------------------------
        # 0. CONSULTA TRIVIAL → responder sin contexto pesado
        # ------------------------------------------------------------
        if self._is_trivial(task):
            logger.info("Consulta trivial: saltando contexto pesado.")
            response = self.agent_manager.delegate(
                task=task,
                context={"query": task},
                skill_name=None,
                skill_params=None,
            )
            self.memory.add(task, response)
            return response

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
        limit = 8 if verbose else 5
        engram_ctx = self.engram.get_context(task, limit=limit)
        if engram_ctx:
            context["engram"] = engram_ctx

        # ------------------------------------------------------------
        # 4. INYECCIÓN DE ESPECIFICACIONES (Specs) si existen
        # ------------------------------------------------------------
        spec = self._find_relevant_spec(task)
        if spec:
            context["spec"] = json.dumps(spec, ensure_ascii=False, indent=2)
            logger.info(
                "Spec encontrada y añadida al contexto: %s",
                spec.get("name"),
            )

        # ------------------------------------------------------------
        # 5. INYECCIÓN DE MEMORIA CONVERSACIONAL (sesión actual)
        # ------------------------------------------------------------
        memory = self.memory.get_context()
        if memory:
            context["memory"] = memory

        # ------------------------------------------------------------
        # 6. DELEGACIÓN AL AGENTE (genera la respuesta)
        # ------------------------------------------------------------
        response = self.agent_manager.delegate(
            task=task,
            context=context,
            skill_name=intent.skill_name,
            skill_params=intent.skill_params,
        )

        # ------------------------------------------------------------
        # 7. SELF-CRITIC (auto-evaluación de la respuesta)
        # ------------------------------------------------------------
        if self._should_critic(task):
            eval_result = self.critic.process(task, context, response)
            if eval_result:
                self.engram.save(
                    json.dumps(eval_result, ensure_ascii=False),
                    tags=[
                        "reflection",
                        "self_critic",
                        f"score_{eval_result.get('alignment_score', 0)}",
                        f"risk_{eval_result.get('hallucination_risk', 'unknown')}",
                    ],
                    async_mode=False,
                )

                logger.info(
                    "Self-Critic guardado | score=%s | risk=%s",
                    eval_result.get("alignment_score"),
                    eval_result.get("hallucination_risk"),
                )

                summary = eval_result.get("summary", "Evaluación no disponible.")
                critic_footer = f"\n\n---\n🤖 **Self-Critic:** {summary}"

                if eval_result.get("hallucination_risk") == "high":
                    critic_footer += (
                        "\n⚠️ **Alerta:** Alto riesgo de alucinación. Verifica el contexto."
                    )
                elif eval_result.get("alignment_score", 0) < 5:
                    critic_footer += (
                        "\n⚠️ **Desviación detectada.** Revisa la recomendación de corrección."
                    )

                response = response + critic_footer

        # ------------------------------------------------------------
        # 8. APRENDIZAJE CONTINUO (detectar correcciones del usuario)
        # ------------------------------------------------------------
        if self.learner.extract_and_learn(task, response):
            logger.info("Nuevo estándar aprendido.")

        # ------------------------------------------------------------
        # 9. PERSISTENCIA EN ENGRAM (guardar la interacción completa)
        # ------------------------------------------------------------
        if not self._is_trivial(task):
            self.engram.save(
                f"Usuario: {task}",
                tags=["user_query", "interaction", "raw"],
            )
            self.engram.save(
                f"Asistente: {response[:500]}",
                tags=["assistant_response", "interaction", "raw"],
            )

        # ------------------------------------------------------------
        # 10. PERSISTENCIA EN MEMORIA CONVERSACIONAL (.history.json)
        # ------------------------------------------------------------
        self.memory.add(task, response)

        return response

    # ================================================================
    # MÉTODOS PRIVADOS
    # ================================================================

    def _find_relevant_spec(self, task: str) -> Optional[dict]:
        """
        Busca una Spec relevante para la tarea.
        Primero por nombre explícito (ej. 'spec mi_proyecto').
        Luego por búsqueda semántica en Engram.
        """
        import re

        # 1. Búsqueda por nombre explícito
        match = re.search(
            r"(?:spec|especificación|plan)\s+['\"]?([a-zA-Z0-9_-]+)['\"]?",
            task,
            re.IGNORECASE,
        )
        if match:
            spec_name = match.group(1)
            spec = self.spec_manager.load_spec_by_name(spec_name)
            if spec:
                logger.info("Spec encontrada por nombre: %s", spec_name)
                return spec

        # 2. Búsqueda semántica en Engram
        memories = self.engram.recall(task, limit=3)
        for m in memories:
            try:
                data = json.loads(m.get("content", "{}"))
                if data.get("type") == "spec":
                    logger.info("Spec encontrada por búsqueda semántica: %s", data.get("name"))
                    return data
            except json.JSONDecodeError:
                continue

        return None

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

    def _is_trivial(self, task: str) -> bool:
        t = task.strip().lower()
        trivial_phrases = {
            "hola",
            "hi",
            "hello",
            "hey",
            "buenas",
            "buenos días",
            "buenos dias",
            "qué tal",
            "que tal",
            "gracias",
            "ok",
            "vale",
            "adios",
            "adiós",
            "chao",
        }
        if t in trivial_phrases:
            return True
        if len(t.split()) <= 2:
            return True
        return False
