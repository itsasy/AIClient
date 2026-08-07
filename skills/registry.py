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
        aliases: list[str] | tuple[str, ...] | None = None,
        overwrite: bool = False,
    ) -> None:

        key = self._normalize(name)

        if not key:
            raise ValueError("Skill requiere nombre válido.")

        self._validate_factory(
            factory,
        )

        if key in self._factories and not overwrite:

            raise ValueError(f"Skill ya registrada: {key}")

        normalized_aliases: list[str] = []

        if aliases:

            for alias in aliases:

                alias_key = self._normalize(alias)

                if not alias_key:
                    continue

                existing = self._aliases.get(
                    alias_key,
                )

                if existing and existing != key and not overwrite:

                    raise ValueError(f"Alias ya registrado: {alias_key}")

                normalized_aliases.append(
                    alias_key,
                )

        # Commit atómico
        self._factories[key] = factory

        for alias_key in normalized_aliases:

            self._aliases[alias_key] = key

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

                raise TypeError("Factory debe producir Skill.")

            return

        if not callable(factory):

            raise TypeError("Factory inválido.")

    # ======================================================
    # Resolution
    # ======================================================

    def get(
        self,
        name: str,
    ) -> Skill | None:

        if not name:
            return None

        key = self._resolve_name(
            name,
        )

        if not key:
            return None

        cached = self._instances.get(
            key,
        )

        if cached:

            return cached

        factory = self._factories.get(
            key,
        )

        if factory is None:

            return None

        instance = self._create_instance(
            key,
            factory,
        )

        if instance is None:

            return None

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

                raise TypeError("Factory no produjo Skill.")

            return instance

        except Exception:

            logger.exception(
                "Error creando Skill=%s",
                name,
            )

            return None

    # ======================================================
    # Query
    # ======================================================

    def has(
        self,
        name: str,
    ) -> bool:

        if not name:

            return False

        return (
            self._resolve_name(
                name,
            )
            in self._factories
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

    def aliases(
        self,
    ) -> dict[str, str]:

        return self._aliases.copy()

    def count(
        self,
    ) -> int:

        return len(
            self._factories,
        )

    def find_by_capability(
        self,
        capability: str,
    ) -> list[Skill]:

        result: list[Skill] = []

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill and skill.supports(
                capability,
            ):

                result.append(
                    skill,
                )

        return result

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        result: dict[str, tuple[str, ...]] = {}

        for name in self.list():

            skill = self.get(
                name,
            )

            if skill:

                result[name] = skill.capabilities

        return result

    # ======================================================
    # Metadata
    # ======================================================

    def metadata(
        self,
    ) -> list[dict[str, Any]]:

        result: list[dict[str, Any]] = []

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

    def unregister(
        self,
        name: str,
    ) -> None:

        if not name:
            return

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
