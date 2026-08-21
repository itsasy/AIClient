from __future__ import annotations

import logging
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
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

    DEFAULT_SYSTEM_PROMPT = "You are a senior software engineer " "and AI coding assistant."

    # Fail-fast: no dejar al SDK reintentar 504 durante minutos
    CONNECT_TIMEOUT = 10.0
    READ_TIMEOUT = 90.0

    def __init__(self) -> None:
        if not Config.NVIDIA_API_KEY:
            raise ProviderAuthenticationError("NVIDIA_API_KEY no está configurada.")

        timeout = httpx.Timeout(
            connect=self.CONNECT_TIMEOUT,
            read=self.READ_TIMEOUT,
            write=30.0,
            pool=10.0,
        )

        self.client = OpenAI(
            api_key=Config.NVIDIA_API_KEY,
            base_url=Config.NVIDIA_BASE_URL,
            timeout=timeout,
            max_retries=0,  # el fallback lo hace ProviderManager
        )

        self.model = Config.NVIDIA_MODEL

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
            raise ProviderError("El prompt no puede estar vacío.")

        selected_model = model or self.model
        selected_system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

        logger.info("NVIDIA NIM request | model=%s", selected_model)

        messages = [
            {"role": "system", "content": selected_system_prompt},
            {"role": "user", "content": prompt},
        ]

        completion_kwargs: dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        for parameter in (
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "stop",
        ):
            if parameter in kwargs:
                completion_kwargs[parameter] = kwargs[parameter]

        try:
            response = self.client.chat.completions.create(**completion_kwargs)

            if not response.choices:
                raise ProviderError("NVIDIA NIM devolvió una respuesta sin opciones.")

            content = response.choices[0].message.content
            if not content:
                raise ProviderError("NVIDIA NIM devolvió una respuesta vacía.")

            return content.strip()

        except AuthenticationError as exc:
            raise ProviderAuthenticationError(
                f"Error de autenticación en NVIDIA NIM: {exc}"
            ) from exc

        except RateLimitError as exc:
            raise ProviderRateLimitError(f"NVIDIA NIM alcanzó el límite de uso: {exc}") from exc

        except (APIConnectionError, APITimeoutError) as exc:
            raise ProviderUnavailableError(
                f"No se pudo conectar / timeout NVIDIA NIM: {exc}"
            ) from exc

        except APIStatusError as exc:
            # 408, 429 ya cubiertos en parte; 5xx y 504 → fallback
            if exc.status_code >= 500 or exc.status_code in {408, 429}:
                raise ProviderUnavailableError(
                    f"NVIDIA NIM no está disponible ({exc.status_code}): {exc}"
                ) from exc
            raise ProviderError(f"Error de NVIDIA NIM: {exc}") from exc

        except (
            ProviderAuthenticationError,
            ProviderRateLimitError,
            ProviderUnavailableError,
            ProviderError,
        ):
            raise

        except Exception as exc:
            logger.exception("Error inesperado en NVIDIA NIM.")
            raise ProviderError(f"Error inesperado en NVIDIA NIM: {exc}") from exc
