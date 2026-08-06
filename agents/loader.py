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
    - Validar contratos básicos.
    - Registrarlas en AgentRegistry.
    - Mantener estado de carga.

    No:

    - Instancia agentes.
    - Ejecuta agentes.
    - Selecciona agentes.
    - Construye contexto.
    """

    DEFAULT_MODULES = [
        "agents.architect",
        "agents.coder",
        "agents.executor",
        "agents.multi_turn",
        "agents.planner",
        "agents.task_agent",
    ]

    def __init__(
        self,
        registry: AgentRegistry,
        modules: list[str] | None = None,
    ):

        self.registry = registry

        self.modules = modules or self.DEFAULT_MODULES.copy()

        self.loaded_modules: set[str] = set()

        self.errors: list[dict[str, str]] = []

    # ======================================================
    # Module loading
    # ======================================================

    def load_module(
        self,
        module_path: str,
    ) -> None:

        if module_path in self.loaded_modules:

            logger.debug(
                "Agent module ya cargado=%s",
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

        except Exception as exc:

            self.errors.append(
                {
                    "module": module_path,
                    "error": str(exc),
                }
            )

            logger.exception(
                "Error cargando Agent module=%s",
                module_path,
            )

    def _register_from_module(
        self,
        module,
    ) -> None:

        for attribute_name in dir(module):

            obj = getattr(
                module,
                attribute_name,
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

            if not hasattr(
                obj,
                "process",
            ):

                logger.warning(
                    "Agent inválido sin process=%s",
                    agent_name,
                )

                continue

            if self.registry.has(
                agent_name,
            ):

                logger.warning(
                    "Agent duplicado ignorado=%s",
                    agent_name,
                )

                continue

            self.registry.register(
                agent_name,
                obj,
            )

            logger.info(
                "Agent registrado=%s capabilities=%s",
                agent_name,
                getattr(
                    obj,
                    "capabilities",
                    (),
                ),
            )

    # ======================================================
    # Defaults
    # ======================================================

    def load_defaults(
        self,
    ) -> None:

        self.load_modules(
            self.modules,
        )

    def load_modules(
        self,
        modules: list[str],
    ) -> None:

        for module in modules:

            self.load_module(
                module,
            )

    # ======================================================
    # Information
    # ======================================================

    def get_errors(
        self,
    ) -> list[dict[str, str]]:

        return self.errors.copy()

    def get_loaded_modules(
        self,
    ) -> list[str]:

        return sorted(
            self.loaded_modules,
        )
