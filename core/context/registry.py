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
    - Exponer catálogo.

    No:

    - Construye contexto.
    - Ejecuta lifecycle.
    - Decide qué contexto requiere un plan.
    """

    def __init__(self):

        self._providers: dict[
            str,
            type[BaseContextProvider],
        ] = {}

        self._aliases: dict[
            str,
            str,
        ] = {}

    # ==================================================
    # Normalization
    # ==================================================

    def _normalize(
        self,
        key: str,
    ) -> str:

        if not key:

            return ""

        return key.lower().strip().replace("-", "_").replace(" ", "_")

    def _resolve(
        self,
        key: str,
    ) -> str:

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

        if not provider:

            raise ValueError("Provider inválido")

        key = self._normalize(provider.key)

        if not key:

            raise ValueError("ContextProvider requiere key")

        if key in self._providers and not overwrite:

            raise ValueError(f"Provider ya registrado: {key}")

        self._providers[key] = provider

        if aliases:

            for alias in aliases:

                alias_key = self._normalize(alias)

                if alias_key:

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

        provider = self._providers.get(resolved)

        if provider is None:

            return None

        return provider()

    def has(
        self,
        key: str,
    ) -> bool:

        return self._resolve(key) in self._providers

    # ==================================================
    # Information
    # ==================================================

    def list(
        self,
    ) -> list[str]:

        return sorted(self._providers.keys())

    def aliases(
        self,
    ) -> dict[str, str]:

        return self._aliases.copy()

    def count(
        self,
    ) -> int:

        return len(self._providers)

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

        aliases = [alias for alias, target in self._aliases.items() if target == resolved]

        for alias in aliases:

            self._aliases.pop(
                alias,
                None,
            )

    def clear(
        self,
    ) -> None:

        self._providers.clear()

        self._aliases.clear()
