from __future__ import annotations

import logging
from collections.abc import Callable

from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registro central de Skills.

    Responsabilidades:

    - Registrar skills.
    - Crear instancias lazy.
    - Resolver ejecución.

    No:

    - Ejecuta skills.
    - Gestiona agentes.
    """

    def __init__(self):

        self._factories: dict[
            str,
            Callable[[], Skill],
        ] = {}

        self._instances: dict[
            str,
            Skill,
        ] = {}

    def register(
        self,
        name: str,
        factory: Callable[[], Skill],
    ):

        key = name.lower().strip()

        self._factories[key] = factory

    def get(
        self,
        name: str,
    ) -> Skill | None:

        key = name.lower().strip()

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(
            key,
        )

        if not factory:

            logger.warning(
                "Skill no registrada=%s",
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

    def list(self):

        return sorted(self._factories.keys())
