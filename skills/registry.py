from __future__ import annotations

import logging

from collections.abc import Callable

from skills.base import Skill

logger = logging.getLogger(__name__)


SkillFactory = Callable[[], Skill] | type[Skill]


class SkillRegistry:
    """
    Registro central de Skills.

    Responsabilidades:

    - Registrar Skills.
    - Crear instancias lazy.
    - Resolver instancias.

    No:

    - Ejecuta Skills.
    - Gestiona planes.
    """

    def __init__(self):

        self._factories: dict[
            str,
            SkillFactory,
        ] = {}

        self._instances: dict[
            str,
            Skill,
        ] = {}

    # ==========================================================
    # Register
    # ==========================================================

    def register(
        self,
        name: str,
        factory: SkillFactory,
    ):

        key = self._normalize(
            name,
        )

        self._factories[key] = factory

        logger.info(
            "Skill registrada=%s",
            key,
        )

    # ==========================================================
    # Resolve
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> Skill | None:

        key = self._normalize(
            name,
        )

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(
            key,
        )

        if factory is None:

            logger.warning(
                "Skill no registrada=%s",
                key,
            )

            return None

        try:

            instance = factory() if callable(factory) else factory

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando skill=%s",
                key,
            )

            return None

    # ==========================================================
    # Information
    # ==========================================================

    def has(
        self,
        name: str,
    ) -> bool:

        return self._normalize(name) in self._factories

    def list(
        self,
    ) -> list[str]:

        return sorted(
            self._factories.keys(),
        )

    # ==========================================================
    # Helpers
    # ==========================================================

    def _normalize(
        self,
        name: str,
    ) -> str:

        return name.lower().strip().replace("-", "_").replace(" ", "_")
