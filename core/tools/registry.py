from __future__ import annotations

import logging

from collections.abc import Callable

from core.tools.base import Tool

logger = logging.getLogger(__name__)


ToolFactory = Callable[[], Tool] | type[Tool]


class ToolRegistry:

    def __init__(self):

        self._factories = {}

        self._instances = {}

    def register(
        self,
        name: str,
        factory: ToolFactory,
    ):

        if isinstance(factory, type):

            if not issubclass(
                factory,
                Tool,
            ):
                raise TypeError("Solo pueden registrarse Tools.")

        self._factories[self._normalize(name)] = factory

    def get(
        self,
        name: str,
    ) -> Tool | None:

        key = self._normalize(name)

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(key)

        if factory is None:

            return None

        try:

            instance = factory()

            if not isinstance(
                instance,
                Tool,
            ):

                raise TypeError("Factory inválida.")

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando Tool=%s",
                key,
            )

            return None

    def has(
        self,
        name: str,
    ) -> bool:

        return self._normalize(name) in self._factories

    def list(
        self,
    ) -> list[str]:

        return sorted(self._factories.keys())

    def metadata(
        self,
    ) -> list[dict]:

        result = []

        for name in self.list():

            tool = self.get(name)

            if tool:

                result.append(tool.get_metadata())

        return result

    def _normalize(
        self,
        name: str,
    ) -> str:

        return name.lower().strip().replace("-", "_").replace(" ", "_")
