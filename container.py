from __future__ import annotations

import logging

from agents.manager import AgentManager
from core.commands.router import CommandRouter
from core.context.manager import ContextManager
from core.context.registry import ContextRegistry
from core.governance.capability_guard import CapabilityGuard
from core.intent import IntentAnalyzer
from core.planning import PlanBuilder
from runtime.execution_engine import ExecutionEngine
from skills.manager import SkillManager

logger = logging.getLogger(__name__)


class ApplicationContainer:
    """
    Punto central de composición del sistema.

    Responsabilidades:
        - Construir dependencias.
        - Conectar runtime.
        - Construir y compartir las dependencias de governance.

    No:
        - Ejecuta tareas.
        - Contiene reglas de negocio.
        - Decide comportamiento.
    """

    def __init__(self) -> None:
        # =====================================================
        # Context
        # =====================================================

        self.context_registry = ContextRegistry()

        self.context_manager = ContextManager(
            registry=self.context_registry,
        )

        # =====================================================
        # Managers / Registries
        # =====================================================

        # Los Managers son responsables de construir y cargar
        # sus respectivos Registries.
        self.agent_manager = AgentManager()
        self.skill_manager = SkillManager()

        # =====================================================
        # Commands
        # =====================================================

        # Registra /spec /plan /build /test /review
        self.command_router = CommandRouter()

        # =====================================================
        # Governance
        # =====================================================

        # Instancia única compartida de CapabilityGuard.
        #
        # El Container es el composition root, por lo que
        # construye la dependencia y la inyecta en el runtime.
        self.capability_guard = CapabilityGuard()

        # =====================================================
        # Execution Engine
        # =====================================================

        # ExecutionEngine consume únicamente los Registries
        # y las dependencias explícitamente inyectadas.
        #
        # El CapabilityGuard se comparte con el Dispatcher
        # a través del ExecutionEngine.
        self.execution_engine = ExecutionEngine(
            agent_registry=self.agent_manager.registry,
            skill_registry=self.skill_manager.registry,
            context_manager=self.context_manager,
            intent_analyzer=IntentAnalyzer(),
            plan_builder=PlanBuilder(),
            command_router=self.command_router,
            capability_guard=self.capability_guard,
        )

        logger.info(
            "Container listo | agents=%s | skills=%s | workflows=%s",
            self.agent_manager.list(),
            self.skill_manager.list(),
            self.command_router.list_commands(),
        )

    # =========================================================
    # Public API
    # =========================================================

    def get_engine(self) -> ExecutionEngine:
        return self.execution_engine

    def resolve(self, name: str):
        mapping = {
            "engine": self.execution_engine,
            "context_manager": self.context_manager,
            "agent_manager": self.agent_manager,
            "skill_manager": self.skill_manager,
            "command_router": self.command_router,
            "agent_registry": self.agent_manager.registry,
            "skill_registry": self.skill_manager.registry,
            "capability_guard": self.capability_guard,
        }

        return mapping.get(name)

    def describe(self) -> dict:
        return {
            "agents": self.agent_manager.list(),
            "skills": self.skill_manager.list(),
            "workflows": self.command_router.list_commands(),
            "context": (
                self.context_manager.describe() if hasattr(self.context_manager, "describe") else {}
            ),
            "governance": {
                "capability_guard": True,
            },
        }


def build_container() -> ApplicationContainer:
    return ApplicationContainer()
