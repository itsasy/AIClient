from __future__ import annotations

import importlib
import logging

from agents.base import Agent
from agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentLoader:
    """
    Descubre y registra agentes.

    No:

    - Ejecuta agentes.
    - Decide selección.
    """

    def __init__(
        self,
        registry: AgentRegistry,
    ):

        self.registry = registry

    def load_module(
        self,
        module_path: str,
    ) -> None:

        try:

            module = importlib.import_module(
                module_path,
            )

            self._register_from_module(
                module,
            )

        except Exception:

            logger.exception(
                "Error cargando agente módulo=%s",
                module_path,
            )

    def _register_from_module(
        self,
        module,
    ) -> None:

        for name in dir(module):

            obj = getattr(
                module,
                name,
            )

            if not isinstance(obj, type):
                continue

            if not issubclass(obj, Agent):
                continue

            if obj is Agent:
                continue

            if obj.__module__ != module.__name__:
                continue

            agent_name = getattr(
                obj,
                "name",
                None,
            )

            if not agent_name:
                continue

            self.registry.register(
                agent_name,
                obj,
            )

    def load_defaults(
        self,
    ) -> None:

        modules = [
            "agents.architect",
            "agents.coder",
            "agents.executor",
            "agents.multi_turn",
            "agents.planner",
            "agents.task_agent",
        ]

        for module in modules:

            self.load_module(
                module,
            )
