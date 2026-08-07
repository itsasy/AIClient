from __future__ import annotations

import logging

from core.context.base import BaseContextProvider

logger = logging.getLogger(__name__)


class ContextRegistry:

    def __init__(self):

        self._providers = {}

    def register(
        self,
        provider: type[BaseContextProvider],
    ):

        key = provider.key

        self._providers[key] = provider

        logger.info(
            "Context provider registrado=%s",
            key,
        )

    def get(
        self,
        key: str,
    ):

        provider = self._providers.get(
            key,
        )

        if not provider:
            return None

        return provider()

    def has(
        self,
        key: str,
    ) -> bool:

        return key in self._providers

    def list(
        self,
    ) -> list[str]:

        return sorted(
            self._providers.keys(),
        )
