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

    - Registrar factories.
    - Resolver instancias lazy.
    - Gestionar aliases.
    - Buscar capacidades.
    - Exponer metadata.

    No:

    - Ejecuta Skills.
    - Gestiona retries.
    - Maneja resultados.
    """

    def __init__(self):

        self._factories: dict[str, SkillFactory] = {}

        self._instances: dict[str, Skill] = {}

        self._aliases: dict[str, str] = {}

    # ======================================================
    # Normalization
    # ======================================================

    def _normalize(
        self,
        name: str,
    ) -> str:

        if not name:

            return ""

        return name.lower().strip().replace("-", "_").replace(" ", "_")

    def _resolve_name(
        self,
        name: str,
    ) -> str:

        key = self._normalize(name)

        return self._aliases.get(
            key,
            key,
        )

    # ======================================================
    # Registration
    # ======================================================

    def register(
        self,
        name: str,
        factory: SkillFactory,
        aliases: list[str] | None = None,
        overwrite: bool = False,
    ) -> None:

        key = self._normalize(name)

        if not key:

            raise ValueError("Skill requiere nombre válido.")

        if key in self._factories and not overwrite:

            raise ValueError(f"Skill ya registrada: {key}")

        self._validate_factory(
            factory,
        )

        self._factories[key] = factory

        if aliases:

            for alias in aliases:

                alias_key = self._normalize(alias)

                if alias_key:

                    self._aliases[alias_key] = key

    def _validate_factory(
        self,
        factory: SkillFactory,
    ):

        if isinstance(factory, type):

            if not issubclass(
                factory,
                Skill,
            ):

                raise TypeError("Factory debe producir Skill.")

        elif not callable(factory):

            raise TypeError("Factory inválido.")

    # ======================================================
    # Resolution
    # ======================================================

    def get(
        self,
        name: str,
    ) -> Skill | None:

        key = self._resolve_name(name)

        if not key:

            return None

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(key)

        if factory is None:

            return None

        try:

            instance = factory()

            if not isinstance(
                instance,
                Skill,
            ):

                raise TypeError("Factory no produjo Skill.")

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando Skill=%s",
                key,
            )

            return None

    # ======================================================
    # Query
    # ======================================================

    def has(
        self,
        name: str,
    ) -> bool:

        return bool(self._resolve_name(name) in self._factories)

    def list(
        self,
    ) -> list[str]:

        return sorted(self._factories.keys())

    def loaded(
        self,
    ) -> list[str]:

        return sorted(self._instances.keys())

    def aliases(
        self,
    ) -> dict[str, str]:

        return self._aliases.copy()

    def count(
        self,
    ) -> int:

        return len(self._factories)

    def find_by_capability(
        self,
        capability: str,
    ) -> list[Skill]:

        result = []

        for name in self.list():

            skill = self.get(name)

            if skill and skill.supports(capability):

                result.append(skill)

        return result

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        result = {}

        for name in self.list():

            skill = self.get(name)

            if skill:

                result[name] = skill.capabilities

        return result

    # ======================================================
    # Metadata
    # ======================================================

    def metadata(
        self,
    ) -> list[dict]:

        result = []

        for name in self.list():

            skill = self.get(name)

            if skill:

                result.append(skill.get_metadata())

        return result

    # ======================================================
    # Management
    # ======================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        key = self._resolve_name(name)

        self._factories.pop(
            key,
            None,
        )

        self._instances.pop(
            key,
            None,
        )

        aliases = [alias for alias, target in self._aliases.items() if target == key]

        for alias in aliases:

            self._aliases.pop(
                alias,
                None,
            )

    def clear(
        self,
    ) -> None:

        self._factories.clear()

        self._instances.clear()

        self._aliases.clear()
