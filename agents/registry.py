from __future__ import annotations

import logging
from collections.abc import Callable

from agents.base import Agent

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registro central de agentes.

    Responsabilidades:

    - Registrar agentes.
    - Resolver instancias lazy.
    - Mantener lifecycle.

    No:

    - Ejecuta agentes.
    - Decide flujo.
    - Construye contexto.
    """

    def __init__(self):

        self._factories: dict[
            str,
            Callable[[], Agent],
        ] = {}

        self._instances: dict[
            str,
            Agent,
        ] = {}

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        name: str,
        factory: Callable[[], Agent],
    ) -> None:

        key = name.lower().strip()

        self._factories[key] = factory

        logger.debug(
            "Agente registrado=%s",
            key,
        )

    # ==========================================================
    # Resolve
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> Agent | None:

        key = name.lower().strip()

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(
            key,
        )

        if factory is None:

            logger.warning(
                "Agente no registrado=%s",
                key,
            )

            return None

        try:

            instance = factory()

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando agente=%s",
                key,
            )

            return None

    # ==========================================================
    # Information
    # ==========================================================

    def contains(
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

    # ==========================================================
    # Management
    # ==========================================================

    def clear(
        self,
    ) -> None:

        self._factories.clear()

        self._instances.clear()
