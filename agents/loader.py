from __future__ import annotations

import importlib
import inspect
import logging

from agents.base import Agent
from agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentLoader:
    """
    Descubrimiento y registro de Agents.

    Responsabilidades:

    - Importar módulos.
    - Detectar implementaciones Agent.
    - Registrarlas en AgentRegistry.

    No:

    - Instancia agentes.
    - Ejecuta agentes.
    - Selecciona agentes.
    """

    def __init__(
        self,
        registry: AgentRegistry,
    ):

        self.registry = registry

        self.loaded_modules: set[str] = set()

    # ==========================================================
    # Module loading
    # ==========================================================

    def load_module(
        self,
        module_path: str,
    ) -> None:

        if module_path in self.loaded_modules:

            logger.debug(
                "Módulo Agent ya cargado=%s",
                module_path,
            )

            return

        try:

            module = importlib.import_module(
                module_path,
            )

            self._register_from_module(
                module,
            )

            self.loaded_modules.add(
                module_path,
            )

        except Exception:

            logger.exception(
                "Error cargando módulo Agent=%s",
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

            if not inspect.isclass(obj):

                continue

            if obj is Agent:

                continue

            if not issubclass(
                obj,
                Agent,
            ):

                continue

            if inspect.isabstract(obj):

                continue

            if obj.__module__ != module.__name__:

                continue

            agent_name = getattr(
                obj,
                "name",
                None,
            )

            if not agent_name:

                logger.warning(
                    "Agent sin nombre ignorado=%s",
                    obj,
                )

                continue

            self.registry.register(
                agent_name,
                obj,
            )

            logger.info(
                "Agent cargado=%s",
                agent_name,
            )

    # ==========================================================
    # Defaults
    # ==========================================================

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
