from __future__ import annotations

import logging

from collections.abc import Callable

from agents.base import Agent

logger = logging.getLogger(__name__)


AgentFactory = Callable[[], Agent] | type[Agent]


class AgentRegistry:
    """
    Registro central de Agents.

    Responsabilidades:

    - Registrar factories.
    - Resolver instancias lazy.
    - Mantener catálogo.
    - Gestionar aliases.

    No:

    - Ejecuta agentes.
    - Decide workflows.
    - Gestiona contexto.
    """

    def __init__(self):

        self._factories: dict[str, AgentFactory] = {}

        self._instances: dict[str, Agent] = {}

        self._aliases: dict[str, str] = {}

    # ======================================================
    # Normalization
    # ======================================================

    def _normalize(
        self,
        name: str,
    ) -> str:

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
        factory: AgentFactory,
        aliases: list[str] | None = None,
        overwrite: bool = False,
    ) -> None:

        key = self._normalize(name)

        if key in self._factories and not overwrite:

            raise ValueError(f"Agent ya registrado: {key}")

        if isinstance(factory, type):

            if not issubclass(factory, Agent):

                raise TypeError("Solo se aceptan clases Agent")

        self._factories[key] = factory

        if aliases:

            for alias in aliases:

                self._aliases[self._normalize(alias)] = key

        logger.info(
            "Agent registrado=%s",
            key,
        )

    # ======================================================
    # Resolution
    # ======================================================

    def get(
        self,
        name: str,
    ) -> Agent | None:

        key = self._resolve_name(name)

        if key in self._instances:

            return self._instances[key]

        factory = self._factories.get(key)

        if factory is None:

            logger.warning(
                "Agent no encontrado=%s",
                key,
            )

            return None

        try:

            instance = factory()

            if not isinstance(instance, Agent):

                raise TypeError("Factory no produjo Agent válido")

            self._instances[key] = instance

            return instance

        except Exception:

            logger.exception(
                "Error creando Agent=%s",
                key,
            )

            return None

    # ======================================================
    # Information
    # ======================================================

    def has(
        self,
        name: str,
    ) -> bool:

        return self._resolve_name(name) in self._factories

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

    def metadata(
        self,
    ) -> list[dict]:

        result = []

        for name in self.list():

            agent = self.get(name)

            if not agent:

                continue

            if hasattr(agent, "get_metadata"):

                result.append(agent.get_metadata())

            else:

                result.append(
                    {
                        "name": agent.name,
                        "description": getattr(
                            agent,
                            "description",
                            "",
                        ),
                        "capabilities": list(
                            getattr(
                                agent,
                                "capabilities",
                                [],
                            )
                        ),
                    }
                )

        return result

    # ======================================================
    # Management
    # ======================================================

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

    def clear(
        self,
    ):

        self._factories.clear()

        self._instances.clear()

        self._aliases.clear()
