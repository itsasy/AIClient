from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registro central de Skills.

    Responsabilidades:

    - Registrar skills.
    - Resolver instancias lazy.
    - Mantener metadata.

    No:

    - Ejecuta skills.
    - Descubre módulos.
    - Gestiona contexto.
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

    # ======================================================
    # Registration
    # ======================================================

    def register(
        self,
        name: str,
        factory: Callable[[], Skill],
    ) -> None:

        key = name.lower().strip()

        self._factories[key] = factory

        logger.debug(
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

        key = name.lower().strip()

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

    def exists(
        self,
        name: str,
    ) -> bool:

        return name.lower().strip() in self._factories

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
    ) -> list[dict[str, Any]]:

        result = []

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill:

                result.append(
                    skill.metadata(),
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
