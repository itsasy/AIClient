import json
import logging
import time
import re

from typing import Optional

from core.config import Config
from core.context_builder import ContextBuilder
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
        self.agent_manager = AgentManager()
        self.learner = ContinuousLearner()
        self.critic = SelfCriticAgent()
        self.spec_manager = SpecManager()

        logger.info("Orchestrator iniciado con Engram + Self-Critic + SpecManager")

    def process(self, task: str, verbose: bool = False) -> str:
        """Procesa una tarea completa del usuario."""
        start_total = time.time()

        # ------------------------------------------------------------
        # 1. ANÁLISIS DE INTENCIÓN
        # ------------------------------------------------------------
        t0 = time.time()

        intent = IntentAnalyzer.analyze(task)

        logger.info("⏱️ IntentAnalyzer: %.3fs", time.time() - t0)
        logger.info(
            "Skill detectada: %s",
            intent.skill_name or "general",
        )
        # ------------------------------------------------------------
        # 2. CONSTRUCCIÓN DE CONTEXTO
        # ------------------------------------------------------------
        t0 = time.time()

        context = self.context_builder.build(task)

        logger.info(
            "⏱️ ContextBuilder.build(): %.3fs",
            time.time() - t0,
        )

        # ------------------------------------------------------------
        # 6. DELEGACIÓN AL AGENTE (LLM PRINCIPAL)
        # ------------------------------------------------------------
        t0 = time.time()

        response = self.agent_manager.delegate(
            task=task,
            context=context,
            skill_name=intent.skill_name,
            skill_params=intent.skill_params,
        )

        logger.info(
            "⏱️ AgentManager.delegate(): %.3fs",
            time.time() - t0,
        )

        # ------------------------------------------------------------
        # 7. SELF-CRITIC (AUTO-EVALUACIÓN)
        # ------------------------------------------------------------
        t0 = time.time()

        if self._should_critic(task):
            eval_result = self.critic.process(
                task,
                context,
                response,
            )

            if eval_result:
                self.engram.save(
                    json.dumps(
                        eval_result,
                        ensure_ascii=False,
                    ),
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

                summary = eval_result.get(
                    "summary",
                    "Evaluación no disponible.",
                )

                critic_footer = f"\n\n---\n🤖 **Self-Critic:** {summary}"

                if eval_result.get("hallucination_risk") == "high":
                    critic_footer += (
                        "\n⚠️ **Alerta:** Alto riesgo de alucinación. " "Verifica el contexto."
                    )
                elif eval_result.get("alignment_score", 0) < 5:
                    critic_footer += (
                        "\n⚠️ **Desviación detectada.** " "Revisa la recomendación de corrección."
                    )

                response += critic_footer

        logger.info(
            "⏱️ Self-Critic (si aplica): %.3fs",
            time.time() - t0,
        )

        # ------------------------------------------------------------
        # 8. APRENDIZAJE CONTINUO
        # ------------------------------------------------------------
        t0 = time.time()

        if self.learner.extract_and_learn(task, response):
            logger.info("Nuevo estándar aprendido. Guardando también en Engram.")

            self.engram.save(
                f"Estándar aprendido: {task[:200]}",
                tags=[
                    "learning",
                    "standard",
                    "continuous_learning",
                ],
            )

        logger.info(
            "⏱️ ContinuousLearner: %.3fs",
            time.time() - t0,
        )

        # ------------------------------------------------------------
        # 9. PERSISTENCIA (ENGRAM + MEMORIA)
        # ------------------------------------------------------------
        t0 = time.time()

        self.engram.save(
            f"Usuario: {task}",
            tags=[
                "user_query",
                "interaction",
                "raw",
            ],
        )

        self.engram.save(
            f"Asistente: {response[:500]}",
            tags=[
                "assistant_response",
                "interaction",
                "raw",
            ],
        )

        self.memory.add(task, response)

        logger.info(
            "⏱️ Persistencia (Engram + Memory): %.3fs",
            time.time() - t0,
        )

        logger.info(
            "⏱️ TOTAL process(): %.3fs",
            time.time() - start_total,
        )

        return response

    # ================================================================
    # MÉTODOS PRIVADOS
    # ================================================================

    def _engram_query(self, task: str) -> str:
        """
        Reduce la pregunta del usuario a términos útiles para FTS de Engram.

        Evita que queries largas del tipo
        "¿puedes decirme mi color favorito?" solo recuperen ecos de user_query
        en lugar de los hechos guardados ("el color favorito es púrpura").
        """
        cleaned = re.sub(r"[¿?¡!.,;:\"'()\[\]{}]", " ", task)
        stop = {
            "el",
            "la",
            "los",
            "las",
            "un",
            "una",
            "unos",
            "unas",
            "de",
            "del",
            "en",
            "y",
            "o",
            "u",
            "a",
            "al",
            "que",
            "qué",
            "cual",
            "cuál",
            "como",
            "cómo",
            "mi",
            "tu",
            "su",
            "mis",
            "tus",
            "sus",
            "me",
            "te",
            "se",
            "le",
            "lo",
            "les",
            "puedes",
            "puedo",
            "puede",
            "pueden",
            "decir",
            "decirme",
            "dime",
            "diga",
            "digame",
            "es",
            "son",
            "está",
            "estan",
            "están",
            "hay",
            "por",
            "para",
            "con",
            "sin",
            "sobre",
            "entre",
            "este",
            "esta",
            "estos",
            "estas",
            "ese",
            "esa",
            "hola",
            "gracias",
            "porfa",
            "porfavor",
            "por favor",
        }
        tokens = [t.lower() for t in cleaned.split() if len(t) > 2 and t.lower() not in stop]
        return " ".join(tokens) if tokens else task.strip()

    def _find_relevant_spec(self, task: str) -> Optional[dict]:
        """Busca una Spec relevante por nombre explícito o por contenido."""
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

        # Búsqueda en disco por nombre suelto al final (ej. auth_module)
        words = task.split()
        if words:
            last = words[-1].strip(".,;:!?\"'")
            if re.match(r"^[a-zA-Z0-9_-]+$", last):
                spec = self.spec_manager.load_spec_by_name(last)
                if spec:
                    return spec

        return None

    def _should_critic(self, task: str) -> bool:
        """Heurística para decidir si la tarea merece auto-evaluación."""
        if not getattr(Config, "ENABLE_SELF_CRITIC", True):
            return False

        words = task.split()
        if len(words) < 5:
            return False

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
