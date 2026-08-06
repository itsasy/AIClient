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

    - Registrar skills.
    - Resolver lazy.
    - Gestionar catálogo.
    - Gestionar aliases.

    No:

    - Ejecuta skills.
    - Maneja retries.
    """

    def __init__(self):

        self._factories: dict[str, SkillFactory] = {}

        self._instances: dict[str, Skill] = {}

        self._aliases: dict[str, str] = {}

    def _normalize(
        self,
        name: str,
    ):

        return name.lower().strip().replace("-", "_").replace(" ", "_")

    def _resolve_name(
        self,
        name: str,
    ):

        key = self._normalize(name)

        return self._aliases.get(
            key,
            key,
        )

    def register(
        self,
        name: str,
        factory: SkillFactory,
        aliases: list[str] | None = None,
        overwrite: bool = False,
    ):

        key = self._normalize(name)

        if key in self._factories and not overwrite:

            raise ValueError(f"Skill ya registrada: {key}")

        if isinstance(factory, type):

            if not issubclass(factory, Skill):

                raise TypeError("Solo se aceptan clases Skill")

        self._factories[key] = factory

        if aliases:

            for alias in aliases:

                self._aliases[self._normalize(alias)] = key

    def get(
        self,
        name: str,
    ) -> Skill | None:

        key = self._resolve_name(name)

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(key)

        if not factory:

            return None

        try:

            instance = factory()

            if not isinstance(instance, Skill):

                raise TypeError("Factory inválido")

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando Skill=%s",
                key,
            )

            return None

    def has(
        self,
        name: str,
    ):

        return self._resolve_name(name) in self._factories

    def list(self):

        return sorted(self._factories.keys())

    def loaded(self):

        return sorted(self._instances.keys())

    def metadata(self):

        result = []

        for name in self.list():

            skill = self.get(name)

            if skill:

                result.append(skill.get_metadata())

        return result

    def unregister(
        self,
        name: str,
    ):

        key = self._resolve_name(name)

        self._factories.pop(
            key,
            None,
        )

        self._instances.pop(
            key,
            None,
        )

    def clear(self):

        self._factories.clear()

        self._instances.clear()

        self._aliases.clear()
