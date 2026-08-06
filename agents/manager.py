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
    - Exponer información.

    No:

    - Ejecuta agentes.
    - Valida planes.
    - Gestiona contexto.
    - Maneja resultados.

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

            self.loader.load_defaults()

    # ==========================================================
    # Resolution
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> Agent | None:

        if not name:

            return None

        return self.registry.get(
            name,
        )

    # ==========================================================
    # Information
    # ==========================================================

    def has(
        self,
        name: str,
    ) -> bool:

        return self.registry.has(
            name,
        )

    def list(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded(
        self,
    ) -> list[str]:

        return self.registry.loaded()

    def metadata(
        self,
    ) -> list[dict]:

        return self.registry.metadata()
