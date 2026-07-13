import logging

from google import genai
from google.genai import errors

from core.config import Config
from llm.base import LLMProvider

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    MODEL = "gemini-2.5-flash"

    def __init__(self):
        self.client = genai.Client(
            api_key=Config.GEMINI_API_KEY
        )

    def generate(self, prompt: str, **kwargs) -> str:
        if not prompt or not prompt.strip():
            return (
                "No se pudo generar una respuesta "
                "porque el prompt está vacío."
            )

        try:
            response = self.client.models.generate_content(
                model=self.MODEL,
                contents=[prompt],
            )

            if not response or not response.text:
                return (
                    "El proveedor respondió correctamente, "
                    "pero no devolvió contenido."
                )

            return response.text

        except errors.ServerError as exc:
            logger.error(
                "Error temporal del servidor de Gemini: %s",
                exc,
            )
            return (
                "El proveedor de IA no está disponible temporalmente. "
                "Intenta ejecutar la consulta nuevamente en unos momentos."
            )

        except errors.APIError as exc:
            logger.error(
                "Error de API de Gemini: %s",
                exc,
            )
            return (
                "No se pudo completar la consulta debido "
                "a un error del proveedor de IA."
            )

        except Exception as exc:
            logger.exception(
                "Error inesperado al generar la respuesta: %s",
                exc,
            )
            return (
                "Ocurrió un error inesperado "
                "al procesar la consulta."
            )