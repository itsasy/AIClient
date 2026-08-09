from __future__ import annotations

import logging
from typing import Any

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

    DEFAULT_SYSTEM_PROMPT = (
        "You are a senior software engineer "
        "and AI coding assistant."
    )

    def __init__(self) -> None:

        if not Config.DEEPSEEK_API_KEY:
            raise ProviderAuthenticationError(
                "DEEPSEEK_API_KEY no está configurada."
            )

        self.client = OpenAI(
            api_key=Config.DEEPSEEK_API_KEY,
            base_url=Config.DEEPSEEK_BASE_URL,
        )

        self.model = Config.DEEPSEEK_MODEL

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> str:

        if not prompt or not prompt.strip():
            raise ProviderError(
                "El prompt no puede estar vacío."
            )

        selected_model = model or self.model

        if kwargs.get("use_coder", False):
            selected_model = Config.DEEPSEEK_CODER_MODEL

        selected_system_prompt = (
            system_prompt or self.DEFAULT_SYSTEM_PROMPT
        )

        logger.info(
            "DeepSeek request | model=%s",
            selected_model,
        )

        try:

            response = self.client.chat.completions.create(
                model=selected_model,
                messages=[
                    {
                        "role": "system",
                        "content": selected_system_prompt,
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )

            if not response.choices:
                raise ProviderError(
                    "DeepSeek devolvió una respuesta sin opciones."
                )

            content = response.choices[0].message.content

            if not content:
                raise ProviderError(
                    "DeepSeek devolvió una respuesta vacía."
                )

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

            raise ProviderError(
                f"Error de DeepSeek: {exc}"
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
                "Error inesperado en DeepSeek."
            )

            raise ProviderError(
                f"Error inesperado en DeepSeek: {exc}"
            ) from exc