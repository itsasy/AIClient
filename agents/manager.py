from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from agents.architect import ArchitectAgent
from agents.base import Agent
from agents.coder import CoderAgent
from agents.executor import ExecutorAgent
from agents.multi_turn import MultiTurnAgent
from agents.planner import PlannerAgent
from agents.task_agent import TaskAgent

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Gestiona agentes disponibles.

    Responsabilidades:

    - Registrar agentes.
    - Resolver agente según ExecutionPlan.
    - Ejecutar agente seleccionado.
    - Mantener fallback seguro.

    No:

    - Analiza intención.
    - Construye contexto.
    - Selecciona proveedores LLM.
    """

    def __init__(self):

        self._factories: dict[
            str,
            Callable[[], Agent],
        ] = {}

        self._agents: dict[
            str,
            Agent,
        ] = {}

        self._register_default_agents()

    # ==========================================================
    # Registration
    # ==========================================================

    def _register_default_agents(
        self,
    ) -> None:

        self.register(
            "architect",
            ArchitectAgent,
        )

        self.register(
            "coder",
            CoderAgent,
        )

        self.register(
            "executor",
            ExecutorAgent,
        )

        self.register(
            "planner",
            PlannerAgent,
        )

        self.register(
            "multi_turn",
            MultiTurnAgent,
        )

        self.register(
            "task",
            TaskAgent,
        )

    def register(
        self,
        name: str,
        factory: Callable[[], Agent],
    ) -> None:

        key = name.lower().strip()

        self._factories[key] = factory

        logger.debug(
            "Agente registrado: %s",
            key,
        )

    # ==========================================================
    # Public API
    # ==========================================================

    def delegate(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> str:

        context = context or {}

        agent = self._select(
            plan,
        )

        if agent is None:

            raise RuntimeError("No existe ningún agente disponible.")

        errors = agent.validate_plan(
            plan,
        )

        if errors:

            logger.warning(
                "Validación del agente %s: %s",
                agent.name,
                errors,
            )

        logger.info(
            "Agent=%s | intent=%s | mode=%s",
            agent.name,
            plan.intent,
            plan.execution_mode,
        )

        return agent.process(
            plan=plan,
            context=context,
        )

    # ==========================================================
    # Selection
    # ==========================================================

    def _select(
        self,
        plan: ExecutionPlan,
    ) -> Agent | None:

        requested = plan.agent

        if requested:

            agent = self._get_agent(
                requested,
            )

            if agent:

                return agent

            logger.warning(
                "Agente solicitado no encontrado: %s",
                requested,
            )

        if plan.execution_mode == "multi_step":

            agent = self._get_agent(
                "planner",
            )

            if agent:

                return agent

        return self._get_agent(
            "task",
        )

    # ==========================================================
    # Lazy loading
    # ==========================================================

    def _get_agent(
        self,
        name: str,
    ) -> Agent | None:

        key = name.lower().strip()

        if key in self._agents:

            return self._agents[key]

        factory = self._factories.get(
            key,
        )

        if factory is None:

            return None

        try:

            agent = factory()

            self._agents[key] = agent

            logger.info(
                "Agente inicializado: %s",
                key,
            )

            return agent

        except Exception:

            logger.exception(
                "No se pudo inicializar agente: %s",
                key,
            )

            return None

    # ==========================================================
    # Debug
    # ==========================================================

    def list_agents(
        self,
    ) -> list[str]:

        return sorted(
            self._factories.keys(),
        )

    def loaded_agents(
        self,
    ) -> list[str]:

        return sorted(
            self._agents.keys(),
        )
