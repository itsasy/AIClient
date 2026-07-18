import re
import logging
from core.standards_learner import StandardsLearner
from llm.provider_manager import ProviderManager
from llm.provider_selector import ProviderSelector

logger = logging.getLogger(__name__)


class ContinuousLearner:
    def __init__(self):
        self.standards = StandardsLearner()
        self.provider_manager = ProviderManager()

    def extract_and_learn(self, user_query: str, assistant_response: str) -> bool:
        """
        Detecta si el usuario está dando una corrección o preferencia,
        extrae el estándar y lo guarda.
        Retorna True si se aprendió algo.
        """
        # 1. Detección rápida por palabras clave (antes de llamar al LLM)
        learn_patterns = [
            r"(aprende|recuerda|guarda|almacena)\s+que\s+(.+?)(?:\.|$)",
            r"(prefiero|prefieres|mejor usar|mejor utiliza)\s+(.+?)(?:\.|$)",
            r"(corrección|corrige|error|debiste|deberías)\s+(.+?)(?:\.|$)",
        ]

        for pattern in learn_patterns:
            match = re.search(pattern, user_query.lower())
            if match:
                # Extraer la frase completa como "key" y usar el LLM para estructurarla
                raw_text = match.group(2).strip()
                return self._learn_from_text(raw_text)

        # 2. Si no hay match directo, preguntar al LLM si hay una corrección implícita
        # (opcional, para evitar falsos positivos)
        return False

    def _learn_from_text(self, text: str) -> bool:
        """Usa el LLM para extraer clave y valor del texto."""
        prompt = f"""
Extrae un estándar o preferencia de aprendizaje del siguiente texto del usuario.

Texto: "{text}"

Devuelve SOLO un JSON válido con dos campos: "key" y "value".
Ejemplo: {{"key": "framework_preferido", "value": "Vue"}}
Si no se puede extraer, devuelve {{"key": null, "value": null}}.
"""
        try:
            provider = ProviderSelector.select(task="learn")
            response = self.provider_manager.generate(prompt, provider_name=provider)

            # Limpiar y parsear JSON
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end != -1:
                response = response[start:end]

            import json

            data = json.loads(response)
            key = data.get("key")
            value = data.get("value")

            if key and value:
                self.standards.learn(key, value)
                logger.info("Aprendido: %s = %s", key, value)
                return True
        except Exception as e:
            logger.debug("No se pudo extraer aprendizaje: %s", e)

        return False

    def get_context(self) -> str:
        """Devuelve los estándares aprendidos formateados para inyectar en prompts."""
        standards = self.standards.list_standards()
        if not standards:
            return ""

        lines = ["=== ESTÁNDARES APRENDIDOS ==="]
        for key, value in standards.items():
            lines.append(f"- {key}: {value}")
        return "\n".join(lines)
