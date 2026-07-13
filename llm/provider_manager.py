import logging
from collections.abc import Callable

from core.config import Config
from llm.base import LLMProvider
from llm.exceptions import (
    AllProvidersFailedError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class ProviderManager:
    def __init__(self):
        self._factories: dict[
            str,
            Callable[[], LLMProvider],
        ] = {}

        self._register_default_providers()

    def _register_default_providers(self) -> None:
        from llm.gemini import GeminiProvider
        from llm.nim import NVIDIAProvider

        self.register(
            "gemini",
            GeminiProvider,
        )

        self.register(
            "nim",
            NVIDIAProvider,
        )

    def register(
        self,
        name: str,
        factory: Callable[[], LLMProvider],
    ) -> None:
        normalized_name = name.strip().lower()

        self._factories[normalized_name] = factory

    def generate(
        self,
        prompt: str,
        provider_name: str | None = None,
        **kwargs,
    ) -> str:
        provider_chain = self._build_provider_chain(
            provider_name,
        )

        errors: dict[str, Exception] = {}

        for name in provider_chain:
            try:
                logger.info(
                    "Intentando provider: %s",
                    name,
                )

                provider = self._create_provider(name)

                response = provider.generate(
                    prompt,
                    **kwargs,
                )

                logger.info(
                    "Provider completado: %s",
                    name,
                )

                return response

            except ProviderError as exc:
                errors[name] = exc

                logger.warning(
                    "Provider %s falló: %s",
                    name,
                    exc,
                )

            except Exception as exc:
                errors[name] = exc

                logger.exception(
                    "Error inesperado en provider %s.",
                    name,
                )

        raise AllProvidersFailedError(errors)

    def _create_provider(
        self,
        name: str,
    ) -> LLMProvider:
        factory = self._factories.get(name)

        if factory is None:
            raise ProviderError(
                f"Provider desconocido: {name}"
            )

        return factory()

    def _build_provider_chain(
        self,
        provider_name: str | None,
    ) -> list[str]:
        primary = (
            provider_name
            or Config.DEFAULT_PROVIDER
        ).strip().lower()

        chain = [primary]

        for fallback in Config.FALLBACK_PROVIDERS:
            normalized_fallback = fallback.strip().lower()

            if (
                normalized_fallback
                and normalized_fallback not in chain
            ):
                chain.append(normalized_fallback)

        return chain