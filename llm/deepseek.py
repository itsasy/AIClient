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


class DeepSeekProvider(LLMProvider):
    name = "deepseek"

    def __init__(self):
        if not Config.DEEPSEEK_API_KEY:
            raise ProviderAuthenticationError("DEEPSEEK_API_KEY no está configurada.")

        self.client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
        )

        # Elegir modelo según el contexto (por defecto el general)
        self.model = Config.DEEPSEEK_MODEL

    def generate(self, prompt: str, **kwargs) -> str:
        if not prompt or not prompt.strip():
            raise ProviderError("El prompt no puede estar vacío.")

        # Si se solicita explícitamente el modelo coder, usarlo
        model = kwargs.get("model", self.model)
        if kwargs.get("use_coder", False):
            model = Config.DEEPSEEK_CODER_MODEL

        logger.info("Enviando solicitud a DeepSeek | Modelo: %s", model)

        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=kwargs.get("temperature", 0.2),
                max_tokens=kwargs.get("max_tokens", 4096),
            )

            if not response.choices:
                raise ProviderError("DeepSeek devolvió una respuesta sin opciones.")

            content = response.choices[0].message.content
            if not content:
                raise ProviderError("DeepSeek devolvió una respuesta vacía.")

            return content.strip()

        except AuthenticationError as exc:
            raise ProviderAuthenticationError(
                f"Error de autenticación en DeepSeek: {exc}"
            ) from exc
        except RateLimitError as exc:
            raise ProviderRateLimitError(
                f"DeepSeek alcanzó el límite de uso: {exc}"
            ) from exc
        except APIConnectionError as exc:
            raise ProviderUnavailableError(
                f"No se pudo conectar con DeepSeek: {exc}"
            ) from exc
        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise ProviderUnavailableError(
                    f"DeepSeek no está disponible: {exc}"
                ) from exc
            raise ProviderError(f"Error de DeepSeek: {exc}") from exc
        except Exception as exc:
            logger.exception("Error inesperado en DeepSeek.")
            raise ProviderError(f"Error inesperado en DeepSeek: {exc}") from exc
