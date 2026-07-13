import logging

from google import genai
from google.genai import errors

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ProviderAuthenticationError(
                "GEMINI_API_KEY no está configurada."
            )

        self.client = genai.Client(
            api_key=Config.GEMINI_API_KEY,
        )

        self.model = Config.GEMINI_MODEL

    def generate(self, prompt: str, **kwargs) -> str:
        if not prompt or not prompt.strip():
            raise ProviderError(
                "El prompt no puede estar vacío."
            )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
            )

            text = getattr(response, "text", None)

            if not text:
                raise ProviderError(
                    "Gemini devolvió una respuesta vacía."
                )

            return text

        except errors.ClientError as exc:
            status_code = getattr(exc, "code", None)

            if status_code in {401, 403}:
                raise ProviderAuthenticationError(
                    f"Error de autenticación en Gemini: {exc}"
                ) from exc

            if status_code == 429:
                raise ProviderRateLimitError(
                    f"Gemini alcanzó el límite de uso: {exc}"
                ) from exc

            raise ProviderError(
                f"Error de cliente en Gemini: {exc}"
            ) from exc

        except errors.ServerError as exc:
            raise ProviderUnavailableError(
                f"Gemini no está disponible temporalmente: {exc}"
            ) from exc

        except (
            ProviderAuthenticationError,
            ProviderRateLimitError,
            ProviderUnavailableError,
            ProviderError,
        ):
            raise

        except errors.APIError as exc:
            raise ProviderError(
                f"Error de API de Gemini: {exc}"
            ) from exc

        except Exception as exc:
            logger.exception(
                "Error inesperado en Gemini."
            )

            raise ProviderError(
                f"Error inesperado en Gemini: {exc}"
            ) from exc