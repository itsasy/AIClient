from __future__ import annotations

import logging

from runtime.registry.agent_registry import AgentRegistry
from agents.loader import AgentLoader
from agents.base import Agent

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Resolver central de Agents.

    Responsabilidades:
    - Mantener catálogo.
    - Resolver agentes.
    - Gestionar carga.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        loader: AgentLoader | None = None,
        auto_load: bool = True,
    ):
        self.registry = registry or AgentRegistry()
        self.loader = loader or AgentLoader(self.registry)
        self.loaded_defaults = False
        if auto_load:
            self.load_defaults()

    def load_defaults(self) -> None:
        if self.loaded_defaults:
            return
        try:
            self.loader.load_defaults()
            self.loaded_defaults = True
        except Exception:
            logger.exception("Error cargando agentes por defecto")

    def load_module(self, module_path: str) -> None:
        try:
            self.loader.load_module(module_path)
        except Exception:
            logger.exception("Error cargando módulo agent=%s", module_path)

    def reload(self) -> None:
        self.clear()
        self.loaded_defaults = False
        self.load_defaults()

    def get(self, name: str) -> Agent | None:
        if not name:
            return None
        return self.registry.get(name)

    def resolve(self, name: str) -> Agent | None:
        return self.get(name)

    def has(self, name: str) -> bool:
        return self.registry.has(name)

    def list(self) -> list[str]:
        return self.registry.list()

    def loaded(self) -> list[str]:
        return self.registry.loaded()

    def aliases(self) -> dict[str, str]:
        return self.registry.aliases()

    def metadata(self) -> list[dict]:
        return self.registry.metadata()

    def unregister(self, name: str) -> None:
        self.registry.unregister(name)

    def clear(self) -> None:
        self.registry.clear()
