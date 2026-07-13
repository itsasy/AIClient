import logging

from google import genai
from google.genai.errors import ServerError

from core.config import Config
from llm.base import LLMProvider


logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    MODEL = "gemini-2.5-flash"

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY no está configurada.")

        self.client = genai.Client(
            api_key=Config.GEMINI_API_KEY
        )

    def generate(self, prompt: str, **kwargs) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=[prompt],
            )

            if not response.text or not response.text.strip():
                return (
                    "Gemini respondió correctamente, "
                    "pero no devolvió contenido."
                )

            return response.text

        except ServerError as exc:
            logger.error(
                "Gemini no está disponible temporalmente: %s",
                exc,
            )

            return (
                "El proveedor Gemini no está disponible temporalmente "
                "(error 503). Intenta nuevamente en unos minutos."
            )

        except Exception as exc:
            logger.exception(
                "Error inesperado al consultar Gemini: %s",
                exc,
            )

            return f"Error al consultar Gemini: {exc}"