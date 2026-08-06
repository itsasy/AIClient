from __future__ import annotations

import importlib
import inspect
import logging

from agents.base import Agent
from agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


class AgentLoader:
    """
    Descubrimiento y registro dinámico de Agents.

    Responsabilidades:

    - Importar módulos.
    - Detectar clases Agent.
    - Registrar factories.
    - Mantener control de módulos cargados.

    No:

    - Instancia agentes.
    - Ejecuta agentes.
    - Selecciona agentes.
    - Gestiona workflows.
    """

    def __init__(
        self,
        registry: AgentRegistry,
    ):

        self.registry = registry

        self.loaded_modules: set[str] = set()

    # ======================================================
    # Module loading
    # ======================================================

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

    # ======================================================
    # Discovery
    # ======================================================

    def _register_from_module(
        self,
        module,
    ) -> None:

        for obj_name in dir(module):

            try:

                obj = getattr(
                    module,
                    obj_name,
                )

            except Exception:

                continue

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

            self._register_agent(
                obj,
            )

    # ======================================================
    # Registration
    # ======================================================

    def _register_agent(
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
                "Agent sin nombre ignorado=%s",
                agent_class,
            )

            return

        aliases = getattr(
            agent_class,
            "aliases",
            None,
        )

        try:

            self.registry.register(
                name=name,
                factory=agent_class,
                aliases=aliases,
            )

            logger.info(
                "Agent cargado=%s aliases=%s",
                name,
                aliases,
            )

        except ValueError:

            logger.debug(
                "Agent ya registrado=%s",
                name,
            )

        except Exception:

            logger.exception(
                "Error registrando Agent=%s",
                name,
            )

    # ======================================================
    # Defaults
    # ======================================================

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
