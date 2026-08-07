from __future__ import annotations

import logging
from typing import Type

from agents.base import Agent
from agents.architect import ArchitectAgent
from agents.planner import PlannerAgent

from runtime.registry.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentLoader:
    """
    Cargador de Agents disponibles para AIClient.

    Responsabilidades:
        - Conocer las implementaciones concretas disponibles.
        - Registrarlas en AgentRegistry.
        - Mantener el runtime desacoplado de los módulos concretos.

    No:
        - Ejecuta Agents.
        - Construye ExecutionPlans.
        - Decide qué Agent utilizar.
    """

    def __init__(
        self,
        registry: AgentRegistry,
    ) -> None:
        self.registry = registry

    # ==========================================================
    # Public API
    # ==========================================================

    def load_defaults(
        self,
    ) -> list[str]:
        """
        Registra los Agents incluidos en la distribución
        estándar de AIClient.
        """

        agents: tuple[Type[Agent], ...] = (
            ArchitectAgent,
            PlannerAgent,
        )

        loaded: list[str] = []

        for agent_class in agents:
            try:
                self._register_agent(
                    agent_class,
                )

                loaded.append(
                    agent_class.name,
                )

            except Exception:
                logger.exception(
                    "No se pudo registrar Agent=%s",
                    getattr(
                        agent_class,
                        "name",
                        agent_class.__name__,
                    ),
                )
                raise

        logger.info(
            "Agents cargados=%s",
            sorted(loaded),
        )

        return sorted(
            loaded,
        )

    # ==========================================================
    # Registration
    # ==========================================================

    def _register_agent(
        self,
        agent_class: Type[Agent],
    ) -> None:
        name = getattr(
            agent_class,
            "name",
            None,
        )

        if not name:
            raise ValueError(
                f"{agent_class.__name__} " "no define name.",
            )

        aliases = getattr(
            agent_class,
            "aliases",
            (),
        )

        self.registry.register(
            name=name,
            factory=agent_class,
            aliases=aliases,
        )

        logger.info(
            "Agent module cargado=%s",
            agent_class.__module__,
        )
