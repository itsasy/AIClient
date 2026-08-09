from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from skills.base import Skill

logger = logging.getLogger(__name__)


class SkillRegistry:
    """
    Registro central y único de Skills.

    Responsabilidades:
        - Registrar clases Skill.
        - Resolver Skills por nombre o alias.
        - Crear instancias.
        - Consultar capabilities.
        - Exponer metadata.

    No:
        - Ejecuta Skills.
        - Construye contexto.
        - Decide qué Skill ejecutar.
        - Gestiona ExecutionPlan.
        - Gestiona lifecycle.
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

                alias_key = self.normalize(
                    alias,
                )

                if not alias_key:
                    continue

                if alias_key in self._skills and alias_key != key:
                    raise ValueError(
                        f"Alias colisiona con Skill: " f"{alias_key}",
                    )

                existing = self._aliases.get(
                    alias_key,
                )

                if existing is not None and existing != key:
                    raise ValueError(
                        f"Alias ya registrado: " f"{alias_key}",
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

        return factory()

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
    # Capabilities
    # ==========================================================

    def capabilities(
        self,
    ) -> dict[str, tuple[str, ...]]:

        result: dict[str, tuple[str, ...]] = {}

        for name in self.list():

            factory = self._skills[name]

            capabilities = getattr(
                factory,
                "capabilities",
                (),
            )

            result[name] = tuple(
                capabilities or (),
            )

        return result

    def find_by_capability(
        self,
        capability: str,
    ) -> list[Skill]:

        target = self.normalize(
            capability,
        )

        if not target:
            return []

        result: list[Skill] = []

        for name in self.list():

            factory = self._skills[name]

            capabilities = getattr(
                factory,
                "capabilities",
                (),
            )

            normalized = {self.normalize(item) for item in capabilities}

            if target in normalized:
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

    # ==========================================================
    # Metadata
    # ==========================================================

    def metadata(
        self,
    ) -> list[dict[str, Any]]:

        result: list[dict[str, Any]] = []

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
