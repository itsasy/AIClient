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
    - Resolver instancias lazy.
    - Mantener catálogo.

    No:

    - Ejecuta Skills.
    - Gestiona ejecución.
    """

    def __init__(self):

        self._factories: dict[str, SkillFactory] = {}

        self._instances: dict[str, Skill] = {}

    # ======================================================
    # Helpers
    # ======================================================

    def _normalize(
        self,
        name: str,
    ) -> str:

        return name.lower().strip().replace("-", "_").replace(" ", "_")

    # ======================================================
    # Register
    # ======================================================

    def register(
        self,
        name: str,
        factory: SkillFactory,
    ) -> None:

        if isinstance(factory, type):

            if not issubclass(
                factory,
                Skill,
            ):

                raise TypeError("Solo pueden registrarse clases Skill.")

        key = self._normalize(
            name,
        )

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

    def contains(
        self,
        name: str,
    ) -> bool:

        return self.has(
            name,
        )

    def list(
        self,
    ) -> list[str]:

        return sorted(
            self._factories.keys(),
        )

    def loaded(
        self,
    ) -> list[str]:

        return sorted(
            self._instances.keys(),
        )

    def metadata(
        self,
    ) -> list[dict]:

        result = []

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill:

                result.append(
                    skill.get_metadata(),
                )

        return result

    # ======================================================
    # Management
    # ======================================================

    def clear(
        self,
    ) -> None:

        self._factories.clear()

        self._instances.clear()
