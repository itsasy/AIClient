from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registro central de Skills.

    Responsabilidades:

    - Registrar Skills.
    - Resolver Skills por nombre o alias.
    - Crear instancias bajo demanda.
    - Consultar capacidades y metadata.

    No:

    - Ejecuta Skills.
    - Gestiona lifecycle.
    - Decide qué Skill ejecutar.
    - Conoce ExecutionEngine.
    """

    def __init__(self) -> None:
        self._skills: dict[str, type[Skill]] = {}
        self._aliases: dict[str, str] = {}

    # ==========================================================
    # Normalization
    # ==========================================================

    @staticmethod
    def normalize(
        value: str | None,
    ) -> str:

        if not value:
            return ""

        return value.lower().strip().replace("-", "_").replace(" ", "_")

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        name: str,
        factory: type[Skill],
        aliases: tuple[str, ...] | list[str] | None = None,
        overwrite: bool = False,
    ) -> None:

        key = self.normalize(name)

        if not key:
            raise ValueError(
                "Skill requiere name.",
            )

        if factory is None:
            raise ValueError(
                f"Factory Skill inválida: {name}",
            )

        if key in self._skills and not overwrite:
            raise ValueError(
                f"Skill ya registrada: {key}",
            )

        validate_definition = getattr(
            factory,
            "validate_definition",
            None,
        )

        if callable(validate_definition):
            errors = validate_definition()

            if errors:
                raise ValueError(
                    f"Skill inválida '{key}': " + "; ".join(errors),
                )

        self._skills[key] = factory

        if aliases:
            for alias in aliases:
                alias_key = self.normalize(alias)

                if not alias_key:
                    continue

                if alias_key in self._aliases and self._aliases[alias_key] != key:
                    raise ValueError(
                        f"Alias de Skill en conflicto: {alias_key}",
                    )

                self._aliases[alias_key] = key

        logger.info(
            "Skill registrada=%s",
            key,
        )

    # ==========================================================
    # Resolution
    # ==========================================================

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

        factory = self._skills.get(key)

        if factory is None:
            logger.warning(
                "Skill no registrada=%s",
                key,
            )
            return None

        try:
            return factory()

        except Exception:
            logger.exception(
                "Error creando Skill=%s",
                key,
            )
            raise

    # ==========================================================
    # Queries
    # ==========================================================

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

    # ==========================================================
    # Capability queries
    # ==========================================================

    def find_by_capability(
        self,
        capability: str,
    ) -> list[Skill]:

        normalized = self.normalize(
            capability,
        )

        result: list[Skill] = []

        for name in self.list():
            factory = self._skills[name]

            capabilities = getattr(
                factory,
                "capabilities",
                (),
            )

            normalized_capabilities = {self.normalize(item) for item in capabilities}

            if normalized in normalized_capabilities:
                result.append(
                    factory(),
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

        result: dict[str, tuple[str, ...]] = {}

        for name in self.list():
            factory = self._skills[name]

            result[name] = tuple(
                getattr(
                    factory,
                    "capabilities",
                    (),
                )
            )

        return result

    # ==========================================================
    # Metadata
    # ==========================================================

    def metadata(
        self,
    ) -> list[dict]:

        result: list[dict] = []

        for name in self.list():
            factory = self._skills[name]

            result.append(
                {
                    "name": name,
                    "description": getattr(
                        factory,
                        "description",
                        "",
                    ),
                    "version": getattr(
                        factory,
                        "version",
                        "",
                    ),
                    "aliases": tuple(
                        getattr(
                            factory,
                            "aliases",
                            (),
                        )
                    ),
                    "capabilities": tuple(
                        getattr(
                            factory,
                            "capabilities",
                            (),
                        )
                    ),
                }
            )

        return result

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        key = self.resolve_name(name)

        self._skills.pop(
            key,
            None,
        )

        self._aliases = {alias: target for alias, target in self._aliases.items() if target != key}

        logger.info(
            "Skill eliminada=%s",
            key,
        )

    def clear(
        self,
    ) -> None:

        self._skills.clear()
        self._aliases.clear()

        logger.info(
            "SkillRegistry limpiado",
        )
