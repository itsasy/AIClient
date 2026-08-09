from __future__ import annotations

import logging

from agents.architect import ArchitectAgent
from agents.base import Agent
from agents.coder import CoderAgent
from agents.executor import ExecutorAgent
from agents.multi_turn import MultiTurnAgent
from agents.task_agent import TaskAgent

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Fachada central para la gestión de Agents.

    Responsabilidades:
        - Coordinar AgentLoader y AgentRegistry.
        - Cargar Agents.
        - Resolver Agents.
        - Consultar metadata.
        - Administrar el catálogo.

    No:
        - Ejecuta Agents.
        - Construye ExecutionPlans.
        - Gestiona el lifecycle de ejecución.
    """

    name = "agent_manager"

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        loader: AgentLoader | None = None,
        auto_load: bool = True,
    ) -> None:
        self.registry = registry or AgentRegistry()

        self.loader = loader or AgentLoader(
            self.registry,
        )

        self.loaded_defaults = False

        if auto_load:
            self.load_defaults()

    # ==========================================================
    # Loading
    # ==========================================================

    def load_defaults(self) -> list[str]:
        if self.loaded_defaults:
            return self.loader.loaded()

        loaded = self.loader.load_defaults()

        self.loaded_defaults = True

        return loaded

    def load_module(
        self,
        module_path: str,
    ) -> bool:
        if not module_path:
            return False

        return self.loader.load_module(
            module_path,
        )

    def reload(self) -> None:
        self.clear()

        self.loader.clear_state()

        self.loaded_defaults = False

        self.load_defaults()

    # ==========================================================
    # Resolution
    # ==========================================================

    def get(
        self,
        name: str | None,
    ) -> Agent | None:
        if not name:
            return None

        return self.registry.get(name)

    def resolve(
        self,
        name: str | None,
    ) -> Agent | None:
        return self.get(name)

    def has(
        self,
        name: str | None,
    ) -> bool:
        if not name:
            return False

        return self.registry.has(name)

    # ==========================================================
    # Registry
    # ==========================================================

    def list(self) -> list[str]:
        return self.registry.list()

    def count(self) -> int:
        return self.registry.count()

    def loaded(self) -> list[str]:
        return self.loader.loaded()

    def aliases(self) -> dict[str, str]:
        return self.registry.aliases()

    def metadata(self) -> list[dict]:
        return self.registry.metadata()

    # ==========================================================
    # Administration
    # ==========================================================

    def unregister(
        self,
        name: str,
    ) -> None:
        if not name:
            return

        self.registry.unregister(name)

    def clear(self) -> None:
        self.registry.clear()
