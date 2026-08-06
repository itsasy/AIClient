from __future__ import annotations


from agents.registry import AgentRegistry
from agents.loader import AgentLoader
from agents.base import Agent


class AgentManager:
    """
    Fachada pública de resolución de Agents.

    Única responsabilidad:

    Resolver agentes disponibles.

    No:

    - Ejecuta.
    - Valida.
    - Gestiona lifecycle.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        loader: AgentLoader | None = None,
    ):

        self.registry = registry or AgentRegistry()

        self.loader = loader or AgentLoader(self.registry)

        self.loader.load_defaults()

    def get(
        self,
        name: str,
    ) -> Agent | None:

        return self.registry.get(name)

    def has(
        self,
        name: str,
    ) -> bool:

        return self.registry.has(name)

    def list(self):

        return self.registry.list()

    def metadata(self):

        return self.registry.metadata()

    def reload(self):

        self.registry.clear()

        self.loader.loaded_modules.clear()

        self.loader.load_defaults()
