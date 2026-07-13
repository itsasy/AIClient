import logging

from google import genai
from google.genai import errors
from google.genai.types import GenerateContentConfig

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

    SYSTEM_PROMPT = (
        "You are a senior software architect "
        "and AI coding assistant."
    )

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ProviderAuthenticationError(
                "GEMINI_API_KEY no está configurada."
            )

        self.client = genai.Client(
            api_key=Config.GEMINI_API_KEY,
        )

        self.model = Config.GEMINI_MODEL

    def generate(
        self,
        prompt: str,
        **kwargs,
    ) -> str:
        if not prompt or not prompt.strip():
            raise ProviderError(
                "El prompt no puede estar vacío."
            )

        logger.info(
            "Enviando solicitud a Gemini | Modelo: %s",
            self.model,
        )

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=GenerateContentConfig(
                    system_instruction=self.SYSTEM_PROMPT,
                    temperature=kwargs.get(
                        "temperature",
                        0.2,
                    ),
                    max_output_tokens=kwargs.get(
                        "max_tokens",
                        4096,
                    ),
                ),
            )

            text = getattr(
                response,
                "text",
                None,
            )

            if text:
                return text.strip()

            candidates = getattr(
                response,
                "candidates",
                None,
            )

            if candidates:
                try:
                    parts = (
                        candidates[0]
                        .content
                        .parts
                    )

                    text = "".join(
                        getattr(
                            part,
                            "text",
                            "",
                        )
                        for part in parts
                    ).strip()

                    if text:
                        return text

                except Exception:
                    logger.debug(
                        "No se pudo extraer texto "
                        "desde candidates de Gemini.",
                        exc_info=True,
                    )

            raise ProviderError(
                "Gemini devolvió una respuesta vacía."
            )

        except errors.ClientError as exc:
            status_code = getattr(
                exc,
                "code",
                None,
            )

            if status_code in (
                401,
                403,
            ):
                raise ProviderAuthenticationError(
                    f"Error de autenticación "
                    f"en Gemini: {exc}"
                ) from exc

            if status_code == 429:
                raise ProviderRateLimitError(
                    f"Gemini alcanzó el límite "
                    f"de uso: {exc}"
                ) from exc

            raise ProviderError(
                f"Error de cliente en Gemini: {exc}"
            ) from exc

        except errors.ServerError as exc:
            raise ProviderUnavailableError(
                "Gemini no está disponible "
                f"temporalmente: {exc}"
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
                "Error inesperado usando Gemini (%s).",
                self.model,
            )

            raise ProviderError(
                f"Error inesperado en Gemini: {exc}"
            ) from exc