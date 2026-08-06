from __future__ import annotations

import logging

from agents.registry import AgentRegistry
from agents.loader import AgentLoader
from agents.base import Agent

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Resolver central de Agents.

    Responsabilidades:

    - Inicializar catálogo.
    - Resolver agentes.
    - Exponer información del catálogo.
    - Administrar ciclo de carga.

    No:

    - Ejecuta agentes.
    - Valida planes.
    - Construye contexto.
    - Gestiona resultados.

    La ejecución pertenece a AgentRuntime.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        loader: AgentLoader | None = None,
        auto_load: bool = True,
    ):

        self.registry = registry or AgentRegistry()

        self.loader = loader or AgentLoader(
            self.registry,
        )

        if auto_load:

            self.load_defaults()

    # ======================================================
    # Loading
    # ======================================================

    def load_defaults(
        self,
    ) -> None:

        self.loader.load_defaults()

    def load_module(
        self,
        module_path: str,
    ) -> None:

        self.loader.load_module(
            module_path,
        )

    # ======================================================
    # Resolution
    # ======================================================

    def get(
        self,
        name: str,
    ) -> Agent | None:

        if not name:

            return None

        return self.registry.get(
            name,
        )

    def has(
        self,
        name: str,
    ) -> bool:

        return self.registry.has(
            name,
        )

    # ======================================================
    # Information
    # ======================================================

    def list(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded(
        self,
    ) -> list[str]:

        return self.registry.loaded()

    def aliases(
        self,
    ) -> dict[str, str]:

        return self.registry.aliases()

    def metadata(
        self,
    ) -> list[dict]:

        return self.registry.metadata()

    # ======================================================
    # Management
    # ======================================================

    def unregister(
        self,
        name: str,
    ) -> None:

        self.registry.unregister(
            name,
        )

    def clear(
        self,
    ) -> None:

        self.registry.clear()
