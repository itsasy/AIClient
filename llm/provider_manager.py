import logging

from llm.base import LLMProvider
from llm.exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class ProviderManager:
    def __init__(
        self,
        providers: list[LLMProvider],
    ):
        if not providers:
            raise ValueError(
                "ProviderManager requiere al menos un proveedor."
            )

        self.providers = providers

    def generate(self, prompt: str, **kwargs) -> str:
        provider_errors = []

        for provider in self.providers:
            if not provider.is_available():
                logger.info(
                    "Proveedor no configurado, se omite: %s",
                    provider.name,
                )
                continue

            try:
                logger.info(
                    "Usando proveedor LLM: %s",
                    provider.name,
                )

                return provider.generate(
                    prompt,
                    **kwargs,
                )

            except LLMProviderError as exc:
                logger.warning(
                    "Proveedor %s falló: %s",
                    provider.name,
                    exc,
                )

                provider_errors.append(
                    f"{provider.name}: {exc}"
                )

        if provider_errors:
            raise LLMProviderError(
                "Todos los proveedores disponibles fallaron. "
                + " | ".join(provider_errors)
            )

        raise LLMProviderError(
            "No hay proveedores LLM configurados."
        )