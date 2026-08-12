from __future__ import annotations

import logging

from core.context.base import BaseContextProvider

logger = logging.getLogger(__name__)


class ContextRegistry:
    """
    Registro central de Context Providers.

    Responsabilidades:

    - Registrar providers.
    - Resolver providers.
    - Gestionar aliases.
    - Mantener instancias de providers.
    - Exponer catálogo.

    No:

    - Construye contexto.
    - Ejecuta lifecycle.
    - Decide qué contexto requiere un plan.
    """

    def __init__(self) -> None:
        self._providers: dict[
            str,
            type[BaseContextProvider],
        ] = {}

        self._instances: dict[
            str,
            BaseContextProvider,
        ] = {}

        self._aliases: dict[
            str,
            str,
        ] = {}

    # ==================================================
    # Normalization
    # ==================================================

    @staticmethod
    def _normalize(key: str) -> str:
        if not isinstance(key, str):
            return ""

        return key.lower().strip().replace("-", "_").replace(" ", "_")

    def _resolve(self, key: str) -> str:
        normalized = self._normalize(key)

        return self._aliases.get(
            normalized,
            normalized,
        )

    # ==================================================
    # Registration
    # ==================================================

    def register(
        self,
        provider: type[BaseContextProvider],
        aliases: list[str] | None = None,
        overwrite: bool = False,
    ) -> None:
        if not isinstance(provider, type):
            raise TypeError("ContextRegistry.register requiere una clase provider.")

        if not issubclass(provider, BaseContextProvider):
            raise TypeError("El provider debe heredar de BaseContextProvider.")

        key = self._normalize(provider.key)

        if not key:
            raise ValueError("ContextProvider requiere key.")

        if key in self._providers and not overwrite:
            raise ValueError(f"Provider ya registrado: {key}")

        self._providers[key] = provider

        # Invalidar instancia anterior si se sobrescribe.
        self._instances.pop(key, None)

        if aliases:
            for alias in aliases:
                alias_key = self._normalize(alias)

                if not alias_key:
                    continue

                self._aliases[alias_key] = key

        logger.info(
            "Context provider registrado=%s",
            key,
        )

    # ==================================================
    # Resolution
    # ==================================================

    def get(
        self,
        key: str,
    ) -> BaseContextProvider | None:
        resolved = self._resolve(key)

        provider_class = self._providers.get(resolved)

        if provider_class is None:
            return None

        instance = self._instances.get(resolved)

        if instance is not None:
            return instance

        instance = provider_class()

        self._instances[resolved] = instance

        return instance

    def has(
        self,
        key: str,
    ) -> bool:
        return self._resolve(key) in self._providers

    # ==================================================
    # Information
    # ==================================================

    def list(self) -> list[str]:
        return sorted(self._providers.keys())

    def aliases(self) -> dict[str, str]:
        return self._aliases.copy()

    def count(self) -> int:
        return len(self._providers)

    def metadata(self) -> list[dict]:
        """
        Devuelve el catálogo descriptivo de providers registrados.
        """

        result = []

        for key in self.list():
            provider = self.get(key)

            if provider is None:
                continue

            result.append(provider.metadata())

        return result

    # ==================================================
    # Management
    # ==================================================

    def unregister(
        self,
        key: str,
    ) -> None:
        resolved = self._resolve(key)

        self._providers.pop(
            resolved,
            None,
        )

        self._instances.pop(
            resolved,
            None,
        )

        aliases = [alias for alias, target in self._aliases.items() if target == resolved]

        for alias in aliases:
            self._aliases.pop(
                alias,
                None,
            )

    def clear(self) -> None:
        self._providers.clear()
        self._instances.clear()
        self._aliases.clear()
