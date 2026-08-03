from __future__ import annotations

import logging
from collections.abc import Callable

from llm.base import LLMProvider
from llm.exceptions import (
    AllProvidersFailedError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Responsable de ejecutar proveedores LLM.

    Responsabilidades:

    - Registrar proveedores.
    - Ejecutar fallback automático.
    - Mantener estadísticas.
    - Futuro soporte para ejecución paralela.
    """

    def __init__(self):

        self._factories: dict[
            str,
            Callable[[], LLMProvider],
        ] = {}

        self._stats = {}

        self._register_default_providers()

    # ---------------------------------------------------------

    def _register_default_providers(self):

        from llm.gemini import GeminiProvider
        from llm.deepseek import DeepSeekProvider
        from llm.nim import NVIDIAProvider

        self.register(
            "gemini",
            GeminiProvider,
        )

        self.register(
            "deepseek",
            DeepSeekProvider,
        )

        self.register(
            "nim",
            NVIDIAProvider,
        )

    # ---------------------------------------------------------

    def register(
        self,
        name: str,
        factory,
    ):

        self._factories[name.lower()] = factory

        self._stats.setdefault(
            name.lower(),
            {
                "calls": 0,
                "success": 0,
                "errors": 0,
            },
        )

    # ---------------------------------------------------------

    def generate(
        self,
        prompt: str,
        provider_name: str,
        fallback_chain: list[str] | None = None,
        **kwargs,
    ) -> str:

        providers = [provider_name]

        if fallback_chain:

            for provider in fallback_chain:

                if provider not in providers:

                    providers.append(provider)

        logger.info(
            "Cadena LLM: %s",
            " -> ".join(providers),
        )

        errors = {}

        for provider in providers:

            try:

                result = self._execute(
                    provider,
                    prompt,
                    **kwargs,
                )

                self._stats[provider]["success"] += 1

                return result

            except Exception as e:

                logger.exception(
                    "Proveedor %s falló.",
                    provider,
                )

                self._stats[provider]["errors"] += 1

                errors[provider] = e

        raise AllProvidersFailedError(errors)

    # ---------------------------------------------------------

    def _execute(
        self,
        provider_name: str,
        prompt: str,
        **kwargs,
    ) -> str:

        provider_name = provider_name.lower()

        factory = self._factories.get(
            provider_name,
        )

        if factory is None:

            raise ProviderError(f"Proveedor desconocido: {provider_name}")

        self._stats[provider_name]["calls"] += 1

        provider = factory()

        return provider.generate(
            prompt,
            **kwargs,
        )

    # ---------------------------------------------------------

    def get_stats(
        self,
    ) -> dict:

        return self._stats
