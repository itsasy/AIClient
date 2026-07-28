from __future__ import annotations

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
    """
    Gestiona los proveedores LLM y ejecuta la cadena de fallbacks.

    Registra fábricas de proveedores y permite ejecutar generaciones
    con una cadena de fallbacks personalizada o por defecto.
    """

    def __init__(self):
        self._factories: dict[str, Callable[[], LLMProvider]] = {}
        self._register_default_providers()

    def _register_default_providers(self) -> None:
        """Registra los proveedores disponibles en el sistema."""
        from llm.gemini import GeminiProvider
        from llm.nim import NVIDIAProvider
        from llm.deepseek import DeepSeekProvider

        self.register("gemini", GeminiProvider)
        self.register("nim", NVIDIAProvider)
        self.register("deepseek", DeepSeekProvider)

        logger.info("Proveedores registrados: gemini, nim, deepseek")

    def register(self, name: str, factory: Callable[[], LLMProvider]) -> None:
        """Registra un nuevo proveedor LLM."""
        normalized_name = name.strip().lower()
        self._factories[normalized_name] = factory

    def generate(
        self,
        prompt: str,
        provider_name: str | None = None,
        fallback_chain: list[str] | None = None,
        **kwargs,
    ) -> str:
        """
        Genera una respuesta usando el proveedor primario y sus fallbacks.

        Args:
            prompt: El prompt a enviar.
            provider_name: Proveedor primario solicitado (opcional).
            fallback_chain: Lista ordenada de proveedores de respaldo.
                           Si es None, se usa la cadena por defecto de Config.
            **kwargs: Argumentos adicionales para el proveedor.

        Returns:
            str: Respuesta generada.

        Raises:
            AllProvidersFailedError: Si todos los proveedores fallan.
        """
        # Construir la cadena de proveedores
        if fallback_chain is None:
            # Cadena por defecto: primario + fallbacks globales
            primary = (provider_name or Config.DEFAULT_PROVIDER).strip().lower()
            chain = [primary]
            for fallback in Config.FALLBACK_PROVIDERS:
                norm_fallback = fallback.strip().lower()
                if norm_fallback and norm_fallback not in chain:
                    chain.append(norm_fallback)
        else:
            # Usar la cadena personalizada, asegurando que el primario esté primero
            if provider_name:
                # Asegurar que el primario está al inicio
                if provider_name not in fallback_chain:
                    chain = [provider_name] + fallback_chain
                else:
                    # Mover el primario al inicio
                    chain = [provider_name] + [
                        p for p in fallback_chain if p != provider_name
                    ]
            else:
                chain = fallback_chain

        logger.info("Cadena de proveedores: %s", " -> ".join(chain))

        errors: dict[str, Exception] = {}

        for name in chain:
            try:
                logger.info("Intentando proveedor: %s", name)
                provider = self._create_provider(name)
                response = provider.generate(prompt, **kwargs)
                logger.info("Proveedor completado: %s", name)
                return response

            except ProviderError as exc:
                errors[name] = exc
                logger.warning("Proveedor %s falló: %s", name, exc)
            except Exception as exc:
                errors[name] = exc
                logger.exception("Error inesperado en proveedor %s.", name)

        raise AllProvidersFailedError(errors)

    def _create_provider(self, name: str) -> LLMProvider:
        """Crea una instancia del proveedor solicitado."""
        factory = self._factories.get(name)
        if factory is None:
            raise ProviderError(f"Proveedor desconocido: {name}")
        return factory()
