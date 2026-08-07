from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from agents.base import Agent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registro central de Agents.

    Responsabilidades:
        - Registrar implementaciones de Agents.
        - Resolver Agents por nombre o alias.
        - Crear instancias bajo demanda.
        - Exponer metadata básica del registro.

    No:
        - Ejecuta Agents.
        - Conoce ExecutionEngine.
        - Conoce ExecutionPlan.
        - Decide qué Agent debe ejecutarse.
    """

    def __init__(self) -> None:
        self._agents: dict[str, Type[Agent]] = {}
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
        factory: Type[Agent],
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

        # ------------------------------------------------------
        # Validar contrato del Agent
        # ------------------------------------------------------

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

        # ------------------------------------------------------
        # Registrar
        # ------------------------------------------------------

        self._agents[key] = factory

        if aliases:
            for alias in aliases:
                alias_key = self.normalize(alias)

                if alias_key:
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

        factory = self._agents.get(
            key,
        )

        if factory is None:
            logger.warning(
                "Agent no registrado=%s",
                key,
            )

            return None

        try:
            return factory()

        except Exception:
            logger.exception(
                "Error creando Agent=%s",
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
    ) -> list[dict]:
        result = []

        for name in self.list():
            factory = self._agents[name]

            metadata_method = getattr(
                factory,
                "metadata",
                None,
            )

            if callable(metadata_method):
                try:
                    result.append(
                        metadata_method(
                            factory(),
                        ),
                    )
                    continue

                except Exception:
                    logger.exception(
                        "No se pudo obtener metadata " "del Agent=%s",
                        name,
                    )

            result.append(
                {
                    "name": name,
                },
            )

        return result

    # ==========================================================
    # Lifecycle
    # ==========================================================

    def unregister(
        self,
        name: str,
    ) -> None:
        key = self.resolve_name(
            name,
        )

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
