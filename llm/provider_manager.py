from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from llm.base import LLMProvider
from llm.exceptions import (
    AllProvidersFailedError,
    ProviderError,
)

logger = logging.getLogger(__name__)


class ProviderManager:
    """
    Runtime manager de proveedores LLM.

    Responsabilidades:

        - Registrar providers.
        - Crear y cachear instancias.
        - Ejecutar providers.
        - Ejecutar fallback.
        - Mantener estadísticas.
        - Exponer información operacional.

    No:

        - Selecciona el provider.
        - Construye prompts.
        - Decide qué modelo utilizar.
        - Conoce ExecutionPlan.
    """

    def __init__(self) -> None:
        self._factories: dict[str, Callable[[], LLMProvider]] = {}
        self._instances: dict[str, LLMProvider] = {}

        self._stats: dict[str, dict[str, int]] = {}

        self._register_default_providers()

    # =========================================================
    # Default providers
    # =========================================================

    def _register_default_providers(self) -> None:
        from llm.providers.deepseek import DeepSeekProvider
        from llm.providers.gemini import GeminiProvider
        from llm.providers.nim import NVIDIAProvider

        self.register("gemini", GeminiProvider)
        self.register("deepseek", DeepSeekProvider)
        self.register("nim", NVIDIAProvider)

    # =========================================================
    # Registration
    # =========================================================

    def register(
        self,
        name: str,
        factory: Callable[[], LLMProvider],
    ) -> None:

        key = self._normalize_name(name)

        if not key:
            raise ValueError("El nombre del provider no puede estar vacío.")

        if not callable(factory):
            raise TypeError(f"La factory del provider '{key}' debe ser callable.")

        self._factories[key] = factory
        self._stats.setdefault(key, self._empty_stats())

        logger.info("Provider registrado=%s", key)

    def unregister(self, name: str) -> None:
        key = self._normalize_name(name)

        self._factories.pop(key, None)
        self._instances.pop(key, None)

        logger.info("Provider eliminado=%s", key)

    # =========================================================
    # Public execution API
    # =========================================================

    def generate(
        self,
        prompt: str,
        provider_name: str,
        fallback_chain: list[str] | None = None,
        **kwargs: Any,
    ) -> str:

        if not prompt or not prompt.strip():
            raise ProviderError("El prompt no puede estar vacío.")

        chain = self._build_chain(
            provider_name,
            fallback_chain,
        )

        logger.info(
            "Cadena LLM=%s",
            " -> ".join(chain),
        )

        errors: dict[str, Exception] = {}

        for provider_name in chain:

            self._ensure_stats(provider_name)

            try:
                return self._execute(
                    provider_name,
                    prompt,
                    **kwargs,
                )

            except Exception as exc:

                self._stats[provider_name]["errors"] += 1
                errors[provider_name] = exc

                logger.warning(
                    "Provider falló | provider=%s | error=%s",
                    provider_name,
                    exc,
                )

        raise AllProvidersFailedError(errors)

    # =========================================================
    # Provider execution
    # =========================================================

    def _execute(
        self,
        provider_name: str,
        prompt: str,
        **kwargs: Any,
    ) -> str:

        provider = self._get_provider(provider_name)

        self._stats[provider_name]["calls"] += 1

        try:
            result = provider.generate(
                prompt,
                **kwargs,
            )

        except Exception:
            raise

        if not isinstance(result, str):
            raise ProviderError(
                f"El provider '{provider_name}' devolvió "
                f"un resultado inválido: {type(result).__name__}"
            )

        result = result.strip()

        if not result:
            raise ProviderError(f"El provider '{provider_name}' devolvió una respuesta vacía.")

        self._stats[provider_name]["success"] += 1

        return result

    # =========================================================
    # Instance management
    # =========================================================

    def _get_provider(
        self,
        provider_name: str,
    ) -> LLMProvider:

        key = self._normalize_name(provider_name)

        factory = self._factories.get(key)

        if factory is None:
            raise ProviderError(f"Proveedor desconocido: {key}")

        if key in self._instances:
            return self._instances[key]

        try:
            instance = factory()

        except Exception as exc:
            logger.exception(
                "No se pudo inicializar provider=%s",
                key,
            )

            raise ProviderError(f"No se pudo inicializar el provider '{key}': {exc}") from exc

        if not isinstance(instance, LLMProvider):
            raise ProviderError(
                f"La factory '{key}' no devolvió una instancia " f"válida de LLMProvider."
            )

        self._instances[key] = instance

        return instance

    # =========================================================
    # Fallback chain
    # =========================================================

    def _build_chain(
        self,
        provider_name: str,
        fallback_chain: list[str] | None,
    ) -> list[str]:

        primary = self._normalize_name(provider_name)

        if not primary:
            raise ProviderError("No se especificó un provider principal.")

        providers = [primary]

        for provider in fallback_chain or []:

            normalized = self._normalize_name(provider)

            if not normalized:
                continue

            if normalized in providers:
                continue

            providers.append(normalized)

        return providers

    # =========================================================
    # Statistics
    # =========================================================

    @staticmethod
    def _empty_stats() -> dict[str, int]:
        return {
            "calls": 0,
            "success": 0,
            "errors": 0,
        }

    def _ensure_stats(self, provider: str) -> None:
        self._stats.setdefault(
            provider,
            self._empty_stats(),
        )

    def get_stats(self) -> dict[str, dict[str, int]]:
        return {name: stats.copy() for name, stats in self._stats.items()}

    def get_provider_stats(
        self,
        name: str,
    ) -> dict[str, int]:

        key = self._normalize_name(name)

        self._ensure_stats(key)

        return self._stats[key].copy()

    # =========================================================
    # Inspection
    # =========================================================

    def list_providers(self) -> list[str]:
        return sorted(self._factories.keys())

    def is_registered(self, name: str) -> bool:
        return self._normalize_name(name) in self._factories

    def is_initialized(self, name: str) -> bool:
        return self._normalize_name(name) in self._instances

    # =========================================================
    # Lifecycle
    # =========================================================

    def reset_instance(self, name: str) -> None:
        key = self._normalize_name(name)

        self._instances.pop(key, None)

        logger.info(
            "Instancia de provider reiniciada=%s",
            key,
        )

    def reset_all_instances(self) -> None:
        self._instances.clear()

        logger.info("Instancias de providers reiniciadas.")

    # =========================================================
    # Helpers
    # =========================================================

    @staticmethod
    def _normalize_name(name: str) -> str:
        return str(name).strip().lower()
