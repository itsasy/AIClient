from __future__ import annotations

import logging

from core.context.manager import ContextManager
from core.context.registry import ContextRegistry

from core.intent import IntentAnalyzer
from core.planning import PlanBuilder

from runtime.execution_engine import ExecutionEngine

from runtime.registry import (
    AgentRegistry,
    SkillRegistry,
)

logger = logging.getLogger(__name__)


class ApplicationContainer:
    """
    Punto central de composición del sistema.

    Responsabilidades:

    - Construir dependencias.
    - Conectar runtime.
    - Registrar componentes.

    No:

    - Ejecuta tareas.
    - Contiene reglas.
    - Decide comportamiento.
    """

    def __init__(self) -> None:

        # ================================
        # Context
        # ================================

        self.context_registry = ContextRegistry()
        self.context_manager = ContextManager(registry=self.context_registry)

        # ================================
        # Registries
        # ================================

        self.agent_registry = AgentRegistry()
        self.skill_registry = SkillRegistry()

        # ================================
        # Load components
        # ================================

        self._register_defaults()

        # ================================
        # Execution Engine
        # ================================

        self.execution_engine = ExecutionEngine(
            agent_registry=self.agent_registry,
            skill_registry=self.skill_registry,
            context_manager=self.context_manager,
            intent_analyzer=IntentAnalyzer(),
            plan_builder=PlanBuilder(),
        )

    # ==================================================
    # Registration
    # ==================================================

    def _register_defaults(self) -> None:
        self._register_agents()
        self._register_skills()
        self._register_context()

    def _register_agents(self) -> None:
        try:
            from agents.loader import AgentLoader

            loader = AgentLoader(self.agent_registry)
            loader.load_defaults()
        except Exception:
            logger.exception("Error cargando Agents")

    def _register_skills(self) -> None:
        try:
            from skills.loader import SkillLoader

            loader = SkillLoader(self.skill_registry)
            loader.load_defaults()
        except Exception:
            logger.exception("Error cargando Skills")

    def _register_context(self) -> None:
        # Punto de extensión para providers
        return

    # ==================================================
    # Public API
    # ==================================================

    def get_engine(self) -> ExecutionEngine:
        return self.execution_engine

    def resolve(self, name: str):
        mapping = {
            "engine": self.execution_engine,
            "context_manager": self.context_manager,
            "agent_registry": self.agent_registry,
            "skill_registry": self.skill_registry,
        }
        return mapping.get(name)

    def describe(self) -> dict:
        return {
            "agents": self.agent_registry.list(),
            "skills": self.skill_registry.list(),
            "context": self.context_manager.describe(),
        }


def build_container() -> ApplicationContainer:
    return ApplicationContainer()
