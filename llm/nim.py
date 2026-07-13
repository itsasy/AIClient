import logging

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderUnavailableError,
)

logger = logging.getLogger(__name__)


class NVIDIAProvider(LLMProvider):
    name = "nim"

    def __init__(self):
        if not Config.NVIDIA_API_KEY:
            raise ProviderAuthenticationError(
                "NVIDIA_API_KEY no está configurada."
            )

        self.client = OpenAI(
            api_key=Config.NVIDIA_API_KEY,
            base_url=Config.NVIDIA_BASE_URL,
        )

        self.model = Config.NVIDIA_MODEL

    def generate(self, prompt: str, **kwargs) -> str:
        if not prompt or not prompt.strip():
            raise ProviderError(
                "El prompt no puede estar vacío."
            )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=kwargs.get(
                    "temperature",
                    0.2,
                ),
            )

            if not response.choices:
                raise ProviderError(
                    "NVIDIA NIM devolvió una respuesta sin opciones."
                )

            content = response.choices[0].message.content

            if not content:
                raise ProviderError(
                    "NVIDIA NIM devolvió una respuesta vacía."
                )

            return content

        except AuthenticationError as exc:
            raise ProviderAuthenticationError(
                f"Error de autenticación en NVIDIA NIM: {exc}"
            ) from exc

        except RateLimitError as exc:
            raise ProviderRateLimitError(
                f"NVIDIA NIM alcanzó el límite de uso: {exc}"
            ) from exc

        except APIConnectionError as exc:
            raise ProviderUnavailableError(
                f"No se pudo conectar con NVIDIA NIM: {exc}"
            ) from exc

        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise ProviderUnavailableError(
                    f"NVIDIA NIM no está disponible: {exc}"
                ) from exc

            raise ProviderError(
                f"Error de NVIDIA NIM: {exc}"
            ) from exc

        except (
            ProviderAuthenticationError,
            ProviderRateLimitError,
            ProviderUnavailableError,
            ProviderError,
        ):
            raise

        except Exception as exc:
            logger.exception(
                "Error inesperado en NVIDIA NIM."
            )

            raise ProviderError(
                f"Error inesperado en NVIDIA NIM: {exc}"
            ) from exc