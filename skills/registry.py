from __future__ import annotations

import logging
from collections.abc import Callable

from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registro central de Skills.

    Responsabilidades:

    - Registrar clases Skill.
    - Crear instancias lazy.
    - Resolver skills.

    No:

    - Ejecuta skills.
    - Gestiona planes.
    - Gestiona contexto.
    """

    def __init__(self):

        self._factories: dict[str, Callable[[], Skill]] = {}

        self._instances: dict[str, Skill] = {}

    def register(
        self,
        name: str,
        factory: Callable[[], Skill],
    ):

        key = self._normalize(name)

        self._factories[key] = factory

        logger.info(
            "Skill registrada=%s",
            key,
        )

    def get(
        self,
        name: str,
    ) -> Skill | None:

        key = self._normalize(name)

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(key)

        if not factory:

            logger.warning(
                "Skill no encontrada=%s",
                key,
            )

            return None

        try:

            instance = factory()

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando skill=%s",
                key,
            )

            return None

    def list(self) -> list[str]:

        return sorted(self._factories.keys())

    def has(
        self,
        name: str,
    ) -> bool:

        return self._normalize(name) in self._factories

    def _normalize(
        self,
        name: str,
    ) -> str:

        return name.lower().strip().replace("-", "_").replace(" ", "_")
