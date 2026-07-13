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
            "Enviando solicitud a NVIDIA NIM "
            "| Modelo: %s | Endpoint: %s",
            self.model,
            Config.NVIDIA_BASE_URL,
        )

        try:
            response = (
                self.client
                .chat
                .completions
                .create(
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
                    max_tokens=kwargs.get(
                        "max_tokens",
                        4096,
                    ),
                )
            )

            if not response.choices:
                raise ProviderError(
                    "NVIDIA NIM devolvió "
                    "una respuesta sin opciones."
                )

            content = (
                response
                .choices[0]
                .message
                .content
            )

            if not content:
                raise ProviderError(
                    "NVIDIA NIM devolvió "
                    "una respuesta vacía."
                )

            return content.strip()

        except AuthenticationError as exc:
            raise ProviderAuthenticationError(
                "Error de autenticación "
                f"en NVIDIA NIM: {exc}"
            ) from exc

        except RateLimitError as exc:
            raise ProviderRateLimitError(
                "NVIDIA NIM alcanzó "
                f"el límite de uso: {exc}"
            ) from exc

        except APIConnectionError as exc:
            raise ProviderUnavailableError(
                "No se pudo conectar "
                f"con NVIDIA NIM: {exc}"
            ) from exc

        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise ProviderUnavailableError(
                    "NVIDIA NIM no está "
                    f"disponible: {exc}"
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
                "Error inesperado "
                f"en NVIDIA NIM: {exc}"
            ) from exc