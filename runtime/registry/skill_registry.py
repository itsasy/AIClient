from __future__ import annotations

import logging

from typing import Type

from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registro central de Skills.

    Responsabilidades:

    - Registrar clases Skill.
    - Resolver instancias.
    - Gestionar aliases.
    - Exponer catálogo.

    No:

    - Ejecuta skills.
    - Decide cuándo usarlas.
    - Gestiona contexto.
    """

    def __init__(
        self,
    ) -> None:

        self._skills: dict[str, Type[Skill]] = {}

        self._aliases: dict[str, str] = {}

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str:

        if not value:
            return ""

        return value.lower().strip().replace("-", "_").replace(" ", "_")

    def register(
        self,
        name: str,
        factory: Type[Skill],
        aliases: tuple[str, ...] | list[str] | None = None,
        overwrite: bool = False,
    ) -> None:

        key = self.normalize(name)

        if not key:
            raise ValueError(
                "Skill requiere name",
            )

        if not factory:
            raise ValueError(
                "Factory Skill inválida",
            )

        if key in self._skills and not overwrite:
            raise ValueError(
                f"Skill ya registrada: {key}",
            )

        self._skills[key] = factory

        if aliases:

            for alias in aliases:

                alias_key = self.normalize(alias)

                if alias_key:
                    self._aliases[alias_key] = key

        logger.info(
            "Skill registrada=%s",
            key,
        )

    def resolve_name(
        self,
        name: str,
    ) -> str:

        key = self.normalize(name)

        return self._aliases.get(
            key,
            key,
        )

    def get(
        self,
        name: str,
    ) -> Skill | None:

        key = self.resolve_name(name)

        factory = self._skills.get(
            key,
        )

        if not factory:
            return None

        return factory()

    def has(
        self,
        name: str,
    ) -> bool:

        return self.resolve_name(name) in self._skills

    def list(
        self,
    ) -> list[str]:

        return sorted(
            self._skills.keys(),
        )

    def count(
        self,
    ) -> int:

        return len(
            self._skills,
        )

    def aliases(
        self,
    ) -> dict[str, str]:

        return dict(
            self._aliases,
        )

    def unregister(
        self,
        name: str,
    ) -> None:

        key = self.resolve_name(
            name,
        )

        self._skills.pop(
            key,
            None,
        )

        self._aliases = {alias: target for alias, target in self._aliases.items() if target != key}

    def clear(
        self,
    ) -> None:

        self._skills.clear()

        self._aliases.clear()
