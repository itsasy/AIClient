from __future__ import annotations

import logging

from core.context.manager import ContextManager
from core.context.registry import ContextRegistry

from core.intent import IntentAnalyzer
from core.planning import PlanBuilder

from runtime import (
    Pipeline,
    ExecutionEngine,
    AgentRuntime,
    SkillRuntime,
)

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

    def __init__(
        self,
    ) -> None:

        # ================================
        # Context
        # ================================

        self.context_registry = ContextRegistry()

        self.context_manager = ContextManager(
            registry=self.context_registry,
        )

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
        # Runtime
        # ================================

        self.agent_runtime = AgentRuntime(
            registry=self.agent_registry,
        )

        self.skill_runtime = SkillRuntime(
            registry=self.skill_registry,
        )

        # ================================
        # Execution
        # ================================

        self.execution_engine = ExecutionEngine(
            agent_runtime=self.agent_runtime,
            skill_runtime=self.skill_runtime,
            context_manager=self.context_manager,
        )

        # ================================
        # Planning
        # ================================

        self.intent_analyzer = IntentAnalyzer()

        self.plan_builder = PlanBuilder()

        # ================================
        # Pipeline
        # ================================

        self.pipeline = Pipeline(
            intent_analyzer=self.intent_analyzer,
            plan_builder=self.plan_builder,
            execution_engine=self.execution_engine,
        )

    # ==================================================
    # Registration
    # ==================================================

    def _register_defaults(
        self,
    ) -> None:

        self._register_agents()

        self._register_skills()

        self._register_context()

    def _register_agents(
        self,
    ) -> None:

        try:

            from agents.loader import AgentLoader

            loader = AgentLoader(
                self.agent_registry,
            )

            loader.load_defaults()

        except Exception:

            logger.exception(
                "Error cargando Agents",
            )

    def _register_skills(
        self,
    ) -> None:

        try:

            from skills.loader import SkillLoader

            loader = SkillLoader(
                self.skill_registry,
            )

            loader.load_defaults()

        except Exception:

            logger.exception(
                "Error cargando Skills",
            )

    def _register_context(
        self,
    ) -> None:
        """
        Punto de extensión para providers.
        """

        return

    # ==================================================
    # Public API
    # ==================================================

    def get_pipeline(
        self,
    ) -> Pipeline:

        return self.pipeline

    def resolve(
        self,
        name: str,
    ):

        mapping = {
            "pipeline": self.pipeline,
            "execution_engine": self.execution_engine,
            "agent_runtime": self.agent_runtime,
            "skill_runtime": self.skill_runtime,
            "context_manager": self.context_manager,
            "agent_registry": self.agent_registry,
            "skill_registry": self.skill_registry,
        }

        return mapping.get(
            name,
        )

    def describe(
        self,
    ) -> dict:

        return {
            "agents": self.agent_registry.list(),
            "skills": self.skill_registry.list(),
            "context": self.context_manager.describe(),
        }


def build_container() -> ApplicationContainer:

    return ApplicationContainer()
