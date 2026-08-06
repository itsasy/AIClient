from __future__ import annotations

import logging

from collections.abc import Callable

from skills.base import Skill

logger = logging.getLogger(__name__)


SkillFactory = Callable[[], Skill] | type[Skill]


class SkillRegistry:

    def __init__(self):

        self._factories: dict[str, SkillFactory] = {}

        self._instances: dict[str, Skill] = {}

    # ======================================================
    # Register
    # ======================================================

    def register(
        self,
        name: str,
        factory: SkillFactory,
    ):

        if isinstance(factory, type):

            if not issubclass(factory, Skill):

                raise TypeError("Solo pueden registrarse clases Skill.")

        key = self._normalize(name)

        self._factories[key] = factory

        logger.info(
            "Skill registrada=%s",
            key,
        )

    # ======================================================
    # Resolve
    # ======================================================

    def get(
        self,
        name: str,
    ) -> Skill | None:

        key = self._normalize(name)

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(key)

        if factory is None:

            return None

        try:

            if isinstance(factory, type):

                instance = factory()

            else:

                instance = factory()

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando skill=%s",
                key,
            )

            return None

    # ======================================================
    # Information
    # ======================================================

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

        for name, factory in self._factories.items():

            if isinstance(factory, type):

                result.append(
                    {
                        "name": factory.name,
                        "description": factory.description,
                        "version": factory.version,
                        "capabilities": list(factory.capabilities),
                    }
                )

            else:

                instance = self.get(name)

                if instance:

                    result.append(instance.get_metadata())

        return result

    # ======================================================
    # Helpers
    # ======================================================

    def _normalize(
        self,
        name: str,
    ) -> str:

        return name.lower().strip().replace("-", "_").replace(" ", "_")
