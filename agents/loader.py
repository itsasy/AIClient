from __future__ import annotations

import importlib
import inspect
import logging
from typing import Type

from agents.base import Agent
from agents.architect import ArchitectAgent
from agents.coder import CoderAgent
from agents.multi_turn import MultiTurnAgent
from agents.task_agent import TaskAgent

from runtime.registry.agent_registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentLoader:
    """
    Descubridor y cargador de Agents.

    Responsabilidades:
        - Conocer los Agents incluidos en la distribución.
        - Cargar módulos dinámicamente.
        - Descubrir implementaciones de Agent.
        - Registrarlas en AgentRegistry.

    No:
        - Ejecuta Agents.
        - Construye ExecutionPlans.
        - Decide qué Agent utilizar.
        - Gestiona el lifecycle de ejecución.
    """

    DEFAULT_AGENTS: tuple[Type[Agent], ...] = (
        ArchitectAgent,
        CoderAgent,
        MultiTurnAgent,
        TaskAgent,
    )

    def __init__(
        self,
        registry: AgentRegistry,
    ) -> None:
        self.registry = registry

        self.loaded_modules: set[str] = set()
        self.failed_modules: set[str] = set()
        self.loaded_agents: set[str] = set()

    # ==========================================================
    # Default loading
    # ==========================================================

    def load_defaults(self) -> list[str]:
        """
        Registra los Agents incluidos en la distribución
        estándar de AIClient.
        """

        loaded: list[str] = []

        for agent_class in self.DEFAULT_AGENTS:
            self._register_agent(agent_class)
            loaded.append(agent_class.name)

        logger.info(
            "Agents cargados=%s",
            sorted(loaded),
        )

        return sorted(loaded)

    # ==========================================================
    # Dynamic module loading
    # ==========================================================

    def load_module(
        self,
        module_path: str,
    ) -> bool:
        """
        Importa un módulo y descubre Agents definidos en él.
        """

        if not module_path:
            return False

        if module_path in self.loaded_modules:
            return True

        try:
            module = importlib.import_module(module_path)

            self._discover_module(module)

            self.loaded_modules.add(module_path)

            logger.info(
                "Módulo Agent cargado=%s",
                module_path,
            )

            return True

        except Exception:
            self.failed_modules.add(module_path)

            logger.exception(
                "Error cargando módulo Agent=%s",
                module_path,
            )

            return False

    def load_modules(
        self,
        modules: list[str] | tuple[str, ...],
    ) -> dict[str, bool]:
        result: dict[str, bool] = {}

        for module_path in modules:
            result[module_path] = self.load_module(
                module_path,
            )

        return result

    # ==========================================================
    # Discovery
    # ==========================================================

    def _discover_module(
        self,
        module,
    ) -> None:
        for _, obj in inspect.getmembers(
            module,
            inspect.isclass,
        ):
            if obj is Agent:
                continue

            if not issubclass(obj, Agent):
                continue

            if inspect.isabstract(obj):
                continue

            if obj.__module__ != module.__name__:
                continue

            self._register_agent(obj)

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
                f"{agent_class.__name__} no define name.",
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

        self.loaded_agents.add(name)

        logger.info(
            "Agent registrado=%s",
            name,
        )

    # ==========================================================
    # Inspection
    # ==========================================================

    def loaded(self) -> list[str]:
        return sorted(
            self.loaded_agents,
        )

    def stats(self) -> dict[str, int]:
        return {
            "modules": len(self.loaded_modules),
            "failed_modules": len(self.failed_modules),
            "agents": len(self.loaded_agents),
        }

    # ==========================================================
    # Reset
    # ==========================================================

    def clear_state(self) -> None:
        self.loaded_modules.clear()
        self.failed_modules.clear()
        self.loaded_agents.clear()
