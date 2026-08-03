import json
import logging
import re

from core.config import Config
from core.engram_memory import EngramMemory
from core.execution_plan import ExecutionPlan
from core.standards_learner import StandardsLearner
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class ContinuousLearner:
    """
    Aprendizaje continuo: detecta correcciones y preferencias del usuario,
    las extrae y las guarda para usarlas en futuras interacciones.

    Almacenamiento dual controlado por Config.LEARNER_BACKEND:
    - "engram": solo Engram (SQLite + FTS5)
    - "legacy": solo `.standards.json`
    - "both": ambos (por defecto)
    """

    def __init__(self):
        self.standards = StandardsLearner()
        self.engram = EngramMemory()
        self.provider_manager = ProviderManager()
        self.backend = getattr(Config, "LEARNER_BACKEND", "both")

        logger.info(
            "ContinuousLearner inicializado (backend: %s)",
            self.backend,
        )

    def extract_and_learn(
        self,
        user_query: str,
        assistant_response: str,
    ) -> bool:
        """
        Detecta si el usuario está dando una corrección o preferencia,
        extrae el estándar y lo guarda.
        """

        learn_patterns = [
            r"(aprende|recuerda|guarda|almacena)\s+que\s+(.+?)(?:\.|$)",
            r"(prefiero|prefieres|mejor usar|mejor utiliza)\s+(.+?)(?:\.|$)",
            r"(corrección|corrige|error|debiste|deberías)\s+(.+?)(?:\.|$)",
            r"(estándar|standard|norma)\s+es\s+(.+?)(?:\.|$)",
        ]

        for pattern in learn_patterns:
            match = re.search(
                pattern,
                user_query.lower(),
            )

            if match:
                raw_text = match.group(2).strip()

                return self._learn_from_text(
                    raw_text,
                    user_query,
                )

        return False

    def _learn_from_text(
        self,
        text: str,
        original_query: str,
    ) -> bool:
        """
        Usa el LLM para extraer clave y valor del texto.
        """

        prompt = f"""
Extrae un estándar o preferencia de aprendizaje del siguiente texto del usuario.

Texto: "{text}"

Devuelve SOLO un JSON válido con dos campos: "key" y "value".

Ejemplo:
{{"key": "framework_preferido", "value": "Vue"}}

Si no se puede extraer, devuelve:
{{"key": null, "value": null}}

REGLAS:
- La "key" debe ser una etiqueta corta y descriptiva (minúsculas, guiones bajos).
- El "value" debe ser el contenido concreto de la preferencia.
- No inventes información que no esté en el texto.
"""

        try:
            plan = ExecutionPlan(
                original_task="learn_extraction",
                intent="learning",
                skills=["learning"],
            )

            provider, fallback = ProviderSelector.select(plan)

            response = self.provider_manager.generate(
                prompt,
                provider_name=provider,
                fallback_chain=fallback,
            )

            start = response.find("{")
            end = response.rfind("}") + 1

            if start != -1 and end != -1:
                response = response[start:end]

            data = json.loads(response)

            key = data.get("key")
            value = data.get("value")

            if key and value:
                self._save_standard(
                    key,
                    value,
                    original_query,
                    text,
                )

                logger.info(
                    "Aprendido: %s = %s",
                    key,
                    value,
                )

                return True

        except Exception as e:
            logger.debug(
                "No se pudo extraer aprendizaje: %s",
                e,
            )

        return False

    def _save_standard(
        self,
        key: str,
        value: str,
        original_query: str,
        raw_text: str,
    ):
        """
        Guarda un estándar según el backend configurado.
        """

        backend = self.backend

        if backend in (
            "legacy",
            "both",
        ):
            self.standards.learn(
                key,
                value,
            )

        if backend in (
            "engram",
            "both",
        ):
            content = f"Estándar aprendido: {key} = {value}"

            tags = [
                "standard",
                "preference",
                "continuous_learning",
                f"key_{key}",
                "trazabilidad",
            ]

            self.engram.save(
                content,
                tags=tags,
                source="continuous_learner",
            )

            context_content = (
                f"Contexto de aprendizaje:\n"
                f"Original: {original_query}\n"
                f"Extraído: {raw_text}\n"
                f"→ {key} = {value}"
            )

            self.engram.save(
                context_content,
                tags=[
                    "learning_context",
                    "trazabilidad",
                    f"key_{key}",
                ],
                source="continuous_learner",
            )

    def get_context(self) -> str:
        """
        Devuelve los estándares aprendidos formateados
        para inyectar en prompts.
        """

        lines = []
        seen_keys = set()

        backend = self.backend

        if backend in (
            "engram",
            "both",
        ):
            memories = self.engram.recall(
                "standard preference",
                limit=10,
            )

            for memory in memories:
                content = memory.get(
                    "content",
                    "",
                )

                if content.startswith("Estándar aprendido:"):
                    try:
                        parts = content.replace(
                            "Estándar aprendido: ",
                            "",
                        ).split(" = ")

                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()

                            if key not in seen_keys:
                                lines.append(f"- {key}: {value}")
                                seen_keys.add(key)

                    except Exception:
                        pass

        if backend in (
            "legacy",
            "both",
        ):
            legacy = self.standards.list_standards()

            for key, value in legacy.items():
                if key not in seen_keys:
                    lines.append(f"- {key}: {value}")
                    seen_keys.add(key)

        if not lines:
            return ""

        return "=== ESTÁNDARES APRENDIDOS ===\n" + "\n".join(lines)

    def learn_direct(
        self,
        key: str,
        value: str,
        context: str = "",
    ) -> bool:
        """
        Aprende un estándar sin utilizar el LLM.
        """

        if not key or not value:
            return False

        self._save_standard(
            key,
            value,
            context or f"Directo: {key} = {value}",
            f"{key} = {value}",
        )

        return True
