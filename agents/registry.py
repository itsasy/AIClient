from __future__ import annotations

import logging

from collections.abc import Callable

from agents.base import Agent

logger = logging.getLogger(__name__)


AgentFactory = Callable[[], Agent] | type[Agent]


class AgentRegistry:
    """
    Registro central de agentes.

    Responsabilidades:

    - Registrar agentes.
    - Resolver instancias lazy.
    - Mantener cache de instancias.
    - Exponer información del catálogo.

    No:

    - Ejecuta agentes.
    - Decide flujos.
    - Construye contexto.
    """

    def __init__(self):

        self._factories: dict[str, AgentFactory] = {}

        self._instances: dict[str, Agent] = {}

    # ==========================================================
    # Helpers
    # ==========================================================

    @staticmethod
    def _normalize(
        name: str,
    ) -> str:

        return (
            name.lower()
            .strip()
            .replace(
                "-",
                "_",
            )
            .replace(
                " ",
                "_",
            )
        )

    # ==========================================================
    # Registration
    # ==========================================================

    def register(
        self,
        name: str,
        factory: AgentFactory,
    ) -> None:

        if isinstance(factory, type):

            if not issubclass(
                factory,
                Agent,
            ):

                raise TypeError("Solo pueden registrarse clases Agent.")

        key = self._normalize(
            name,
        )

        self._factories[key] = factory

        logger.info(
            "Agent registrado=%s",
            key,
        )

    # ==========================================================
    # Resolution
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> Agent | None:

        key = self._normalize(
            name,
        )

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(
            key,
        )

        if factory is None:

            logger.warning(
                "Agent no registrado=%s",
                key,
            )

            return None

        try:

            if isinstance(
                factory,
                type,
            ):

                instance = factory()

            else:

                instance = factory()

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando agent=%s",
                key,
            )

            return None

    # ==========================================================
    # Information
    # ==========================================================

    def has(
        self,
        name: str,
    ) -> bool:

        return (
            self._normalize(
                name,
            )
            in self._factories
        )

    def contains(
        self,
        name: str,
    ) -> bool:

        return self.has(
            name,
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

    def metadata(
        self,
    ) -> list[dict]:

        result = []

        for name in self.list():

            agent = self.get(
                name,
            )

            if agent is None:

                continue

            if hasattr(
                agent,
                "get_metadata",
            ):

                result.append(
                    agent.get_metadata(),
                )

            else:

                result.append(
                    {
                        "name": agent.name,
                        "description": getattr(
                            agent,
                            "description",
                            "",
                        ),
                        "version": getattr(
                            agent,
                            "version",
                            "1.0",
                        ),
                        "capabilities": list(
                            getattr(
                                agent,
                                "capabilities",
                                (),
                            )
                        ),
                    }
                )

        return result

    # ==========================================================
    # Management
    # ==========================================================

    def clear(
        self,
    ) -> None:

        self._factories.clear()

        self._instances.clear()
