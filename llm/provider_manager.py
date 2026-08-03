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
    Ejecuta proveedores LLM.

    Responsabilidades:

    - Registrar proveedores.
    - Ejecutar fallback automático.
    - Mantener estadísticas.
    - Administrar ciclo de vida de providers.
    """

    def __init__(self):

        self._factories: dict[
            str,
            Callable[[], LLMProvider],
        ] = {}

        self._instances: dict[
            str,
            LLMProvider,
        ] = {}

        self._stats: dict[
            str,
            dict[str, int],
        ] = {}

        self._register_default_providers()

    # =========================================================
    # Registro inicial
    # =========================================================

    def _register_default_providers(
        self,
    ) -> None:

        from llm.providers.deepseek import DeepSeekProvider
        from llm.providers.gemini import GeminiProvider
        from llm.providers.nim import NVIDIAProvider

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

    # =========================================================
    # Registro
    # =========================================================

    def register(
        self,
        name: str,
        factory: Callable[[], LLMProvider],
    ) -> None:

        key = name.lower().strip()

        self._factories[key] = factory

        self._stats.setdefault(
            key,
            self._empty_stats(),
        )

    def unregister(
        self,
        name: str,
    ) -> None:

        key = name.lower().strip()

        self._factories.pop(
            key,
            None,
        )

        self._instances.pop(
            key,
            None,
        )

    # =========================================================
    # Ejecución pública
    # =========================================================

    def generate(
        self,
        prompt: str,
        provider_name: str,
        fallback_chain: list[str] | None = None,
        **kwargs,
    ) -> str:

        providers = self._build_chain(
            provider_name,
            fallback_chain,
        )

        logger.info(
            "Cadena LLM: %s",
            " -> ".join(providers),
        )

        errors: dict[str, Exception] = {}

        for provider in providers:

            self._ensure_stats(
                provider,
            )

            try:

                result = self._execute(
                    provider,
                    prompt,
                    **kwargs,
                )

                self._stats[provider]["success"] += 1

                return result

            except Exception as exc:

                logger.exception(
                    "Proveedor %s falló.",
                    provider,
                )

                self._stats[provider]["errors"] += 1

                errors[provider] = exc

        raise AllProvidersFailedError(
            errors,
        )

    # =========================================================
    # Ejecución interna
    # =========================================================

    def _execute(
        self,
        provider_name: str,
        prompt: str,
        **kwargs,
    ) -> str:

        factory = self._factories.get(
            provider_name,
        )

        if factory is None:

            raise ProviderError(f"Proveedor desconocido: {provider_name}")

        self._stats[provider_name]["calls"] += 1

        provider = self._get_instance(
            provider_name,
            factory,
        )

        return provider.generate(
            prompt,
            **kwargs,
        )

    # =========================================================
    # Instancias
    # =========================================================

    def _get_instance(
        self,
        name: str,
        factory: Callable[[], LLMProvider],
    ) -> LLMProvider:

        if name not in self._instances:

            try:

                self._instances[name] = factory()

            except Exception as exc:

                logger.exception(
                    "No se pudo inicializar provider %s",
                    name,
                )

                raise ProviderError(f"No se pudo inicializar {name}: {exc}") from exc

        return self._instances[name]

    # =========================================================
    # Helpers
    # =========================================================

    def _build_chain(
        self,
        provider_name: str,
        fallback_chain: list[str] | None,
    ) -> list[str]:

        providers = [provider_name.lower().strip()]

        for provider in fallback_chain or []:

            provider = provider.lower().strip()

            if provider and provider not in providers:

                providers.append(
                    provider,
                )

        return providers

    @staticmethod
    def _empty_stats() -> dict[str, int]:

        return {
            "calls": 0,
            "success": 0,
            "errors": 0,
        }

    def _ensure_stats(
        self,
        provider: str,
    ) -> None:

        self._stats.setdefault(
            provider,
            self._empty_stats(),
        )

    # =========================================================
    # Administración
    # =========================================================

    def list_providers(
        self,
    ) -> list[str]:

        return sorted(
            self._factories.keys(),
        )

    def get_stats(
        self,
    ) -> dict[str, dict[str, int]]:

        return {name: stats.copy() for name, stats in self._stats.items()}
