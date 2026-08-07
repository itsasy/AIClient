from __future__ import annotations

import importlib
import inspect
import logging

from agents.base import Agent

from runtime.registry.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentLoader:
    """
    Cargador dinámico de Agents.

    Responsabilidades:

    - Importar módulos.
    - Descubrir Agents.
    - Registrar clases.

    No:

    - Ejecuta Agents.
    - Instancia Agents.
    - Decide resolución.
    """

    def __init__(
        self,
        registry: AgentRegistry,
    ) -> None:

        self.registry = registry

        self.loaded_modules: set[str] = set()

        self.loaded_agents: set[str] = set()

    # ==================================================
    # Loading
    # ==================================================

    def load_defaults(
        self,
    ) -> None:

        modules = [
            "agents.architect",
            "agents.coder",
            "agents.executor",
            "agents.multi_turn",
            "agents.parallel",
            "agents.planner",
            "agents.task_agent",
        ]

        self.load_modules(
            modules,
        )

    def load_modules(
        self,
        modules: list[str],
    ) -> None:

        for module in modules:

            self.load_module(
                module,
            )

    def load_module(
        self,
        module_path: str,
    ) -> None:

        if module_path in self.loaded_modules:

            return

        try:

            module = importlib.import_module(
                module_path,
            )

            agents = self.discover(
                module,
            )

            for agent_class in agents:

                self.register(
                    agent_class,
                )

            self.loaded_modules.add(
                module_path,
            )

        except Exception:

            logger.exception(
                "Error cargando Agent module=%s",
                module_path,
            )

    # ==================================================
    # Discovery
    # ==================================================

    def discover(
        self,
        module,
    ) -> list[type[Agent]]:

        result: list[type[Agent]] = []

        for obj_name in dir(module):

            obj = getattr(
                module,
                obj_name,
                None,
            )

            if not inspect.isclass(obj):

                continue

            if obj is Agent:

                continue

            if not issubclass(
                obj,
                Agent,
            ):

                continue

            if inspect.isabstract(
                obj,
            ):

                continue

            if obj.__module__ != module.__name__:

                continue

            result.append(
                obj,
            )

        return result

    # ==================================================
    # Registration
    # ==================================================

    def register(
        self,
        agent_class: type[Agent],
    ) -> None:

        name = getattr(
            agent_class,
            "name",
            None,
        )

        if not name:

            logger.warning(
                "Agent sin name=%s",
                agent_class,
            )

            return

        try:

            self.registry.register(
                agent_class,
            )

            self.loaded_agents.add(
                name,
            )

            logger.info(
                "Agent cargado=%s",
                name,
            )

        except ValueError:

            logger.debug(
                "Agent ya registrado=%s",
                name,
            )

    # ==================================================
    # Information
    # ==================================================

    def stats(
        self,
    ) -> dict:

        return {
            "modules": len(
                self.loaded_modules,
            ),
            "agents": len(
                self.loaded_agents,
            ),
        }
