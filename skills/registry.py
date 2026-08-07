from __future__ import annotations

import logging

from collections.abc import Callable
from typing import Any

from skills.base import Skill

logger = logging.getLogger(__name__)


SkillFactory = Callable[[], Skill] | type[Skill]


class SkillRegistry:
    """
    Registro central de Skills.

    Responsabilidades:

    - Registrar Skills.
    - Resolver aliases.
    - Crear instancias lazy.
    - Exponer catálogo.
    - Buscar capacidades.

    No:

    - Ejecuta Skills.
    - Gestiona retries.
    - Gestiona resultados.
    """

    def __init__(
        self,
    ) -> None:

        self._factories: dict[str, SkillFactory] = {}

        self._instances: dict[str, Skill] = {}

        self._aliases: dict[str, str] = {}

    # ==================================================
    # Normalization
    # ==================================================

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str:

        if not value:
            return ""

        return value.lower().strip().replace("-", "_").replace(" ", "_")

    def _resolve_name(
        self,
        name: str,
    ) -> str:

        key = self.normalize(
            name,
        )

        return self._aliases.get(
            key,
            key,
        )

    # ==================================================
    # Registration
    # ==================================================

    def register(
        self,
        name: str,
        factory: SkillFactory,
        aliases: tuple[str, ...] | list[str] | None = None,
        overwrite: bool = False,
    ) -> None:

        key = self.normalize(
            name,
        )

        if not key:

            raise ValueError(
                "Skill requiere nombre.",
            )

        self._validate_factory(
            factory,
        )

        if key in self._factories and not overwrite:

            raise ValueError(
                f"Skill ya registrada: {key}",
            )

        normalized_aliases: list[str] = []

        for alias in aliases or ():

            alias_key = self.normalize(
                alias,
            )

            if not alias_key:
                continue

            if alias_key == key:
                continue

            existing = self._aliases.get(
                alias_key,
            )

            if existing and existing != key and not overwrite:

                raise ValueError(
                    f"Alias ya registrado: {alias_key}",
                )

            if alias_key in self._factories and alias_key != key and not overwrite:

                raise ValueError(
                    f"Alias coincide con Skill: {alias_key}",
                )

            normalized_aliases.append(
                alias_key,
            )

        self._factories[key] = factory

        for alias in normalized_aliases:

            self._aliases[alias] = key

    def _validate_factory(
        self,
        factory: SkillFactory,
    ) -> None:

        if isinstance(
            factory,
            type,
        ):

            if not issubclass(
                factory,
                Skill,
            ):

                raise TypeError(
                    "Factory debe producir Skill.",
                )

            return

        if not callable(factory):

            raise TypeError(
                "Factory inválido.",
            )

    # ==================================================
    # Resolution
    # ==================================================

    def get(
        self,
        name: str | None,
    ) -> Skill | None:

        if not name:
            return None

        key = self._resolve_name(
            name,
        )

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(
            key,
        )

        if factory is None:

            return None

        instance = self._create_instance(
            key,
            factory,
        )

        if instance:

            self._instances[key] = instance

        return instance

    def _create_instance(
        self,
        name: str,
        factory: SkillFactory,
    ) -> Skill | None:

        try:

            instance = factory()

            if not isinstance(
                instance,
                Skill,
            ):

                raise TypeError(
                    f"La factory '{name}' no produjo Skill.",
                )

            return instance

        except Exception:

            logger.exception(
                "Error creando Skill=%s",
                name,
            )

            return None

    # ==================================================
    # Query
    # ==================================================

    def has(
        self,
        name: str | None,
    ) -> bool:

        if not name:
            return False

        return self._resolve_name(name) in self._factories

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

    def count(
        self,
    ) -> int:

        return len(
            self._factories,
        )

    def aliases(
        self,
    ) -> dict[str, str]:

        return self._aliases.copy()

    # ==================================================
    # Capability search
    # ==================================================

    def find_by_capability(
        self,
        capability: str,
    ) -> list[Skill]:

        result: list[Skill] = []

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill and skill.supports(capability):

                result.append(
                    skill,
                )

        return result

    def contains_capability(
        self,
        capability: str,
    ) -> bool:

        return bool(
            self.find_by_capability(
                capability,
            )
        )

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        result = {}

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill:

                result[name] = skill.capabilities

        return result

    # ==================================================
    # Metadata
    # ==================================================

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
                    skill.get_metadata(),
                )

        return result

    # ==================================================
    # Management
    # ==================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        key = self._resolve_name(
            name,
        )

        self._factories.pop(
            key,
            None,
        )

        self._instances.pop(
            key,
            None,
        )

        for alias, target in list(
            self._aliases.items(),
        ):

            if target == key:

                self._aliases.pop(
                    alias,
                )

    def clear(
        self,
    ) -> None:

        self._factories.clear()

        self._instances.clear()

        self._aliases.clear()
