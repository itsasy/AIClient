from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents.base import Agent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registro central y único de Agents.

    Responsabilidades:
        - Registrar clases Agent.
        - Resolver Agents por nombre o alias.
        - Crear instancias.
        - Exponer metadata.

    No:
        - Ejecuta Agents.
        - Decide qué Agent ejecutar.
        - Gestiona ExecutionPlan.
        - Gestiona lifecycle.
    """

    def __init__(self) -> None:
        self._agents: dict[str, type[Agent]] = {}
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
        factory: type[Agent],
        aliases: tuple[str, ...] | list[str] | None = None,
        overwrite: bool = False,
    ) -> None:

        key = self.normalize(name)

        if not key:
            raise ValueError(
                "Agent requiere name.",
            )

        if factory is None:
            raise ValueError(
                f"Factory Agent inválida: {name}",
            )

        if key in self._agents and not overwrite:
            raise ValueError(
                f"Agent ya registrado: {key}",
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
                    f"Agent inválido '{key}': " + "; ".join(errors),
                )

        self._agents[key] = factory

        if aliases:

            for alias in aliases:

                alias_key = self.normalize(
                    alias,
                )

                if not alias_key:
                    continue

                if alias_key in self._agents and alias_key != key:
                    raise ValueError(
                        f"Alias colisiona con Agent: " f"{alias_key}",
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
            "Agent registrado=%s",
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
    ) -> Agent | None:

        key = self.resolve_name(name)

        factory = self._agents.get(key)

        if factory is None:
            logger.warning(
                "Agent no registrado=%s",
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

        return self.resolve_name(name) in self._agents

    def list(
        self,
    ) -> list[str]:

        return sorted(
            self._agents.keys(),
        )

    def count(
        self,
    ) -> int:

        return len(
            self._agents,
        )

    def aliases(
        self,
    ) -> dict[str, str]:

        return dict(
            self._aliases,
        )

    # ==========================================================
    # Metadata
    # ==========================================================

    def metadata(
        self,
    ) -> list[dict[str, Any]]:

        result: list[dict[str, Any]] = []

        for name in self.list():

            factory = self._agents[name]

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

        self._agents.pop(
            key,
            None,
        )

        self._aliases = {alias: target for alias, target in self._aliases.items() if target != key}

        logger.info(
            "Agent eliminado=%s",
            key,
        )

    def clear(
        self,
    ) -> None:

        self._agents.clear()
        self._aliases.clear()

        logger.info(
            "AgentRegistry limpiado",
        )
