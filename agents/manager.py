from __future__ import annotations

import logging
from typing import Any

from agents.base import Agent
from agents.registry import AgentRegistry
from agents.loader import AgentLoader

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class AgentManager:
    """
    Gestiona ejecución de agentes.

    Responsabilidades:

    - Seleccionar agente.
    - Validar plan.
    - Delegar ejecución.

    No:

    - Registra agentes.
    - Descubre módulos.
    - Construye contexto.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        loader: AgentLoader | None = None,
    ):

        self.registry = registry or AgentRegistry()

        self.loader = loader or AgentLoader(
            self.registry,
        )

        self.loader.load_defaults()

    # ==========================================================
    # Agent normalization
    # ==========================================================

    def _normalize_agent(
        self,
        name: str | None,
    ) -> str | None:

        if not name:

            return None

        return name.lower().strip().replace(" ", "_").replace("-", "_")

    # ==========================================================
    # Delegation
    # ==========================================================

    def delegate(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> Any:

        context = context or {}

        if plan.agent:

            plan.agent = self._normalize_agent(plan.agent)

        agent = self._select(
            plan,
        )

        if agent is None:

            raise RuntimeError("No existe agente disponible.")

        errors = agent.validate_plan(
            plan,
        )

        if errors:

            logger.warning(
                "Validación agente=%s errores=%s",
                agent.name,
                errors,
            )

            plan.metadata.setdefault(
                "agent_validation_errors",
                [],
            )

            plan.metadata["agent_validation_errors"].extend(errors)

        return agent.process(
            plan,
            context,
        )

    # ==========================================================
    # Selection
    # ==========================================================

    def _select(
        self,
        plan: ExecutionPlan,
    ) -> Agent | None:

        agent_name = self._normalize_agent(plan.agent)

        if agent_name:

            agent = self.registry.get(
                agent_name,
            )

            if agent:

                return agent

        if plan.execution_mode == "multi_step":

            agent = self.registry.get(
                "planner",
            )

            if agent:

                return agent

        return self.registry.get(
            "task",
        )

    # ==========================================================
    # Access
    # ==========================================================

    def get(
        self,
        name: str,
    ) -> Agent | None:

        normalized = self._normalize_agent(name)

        if not normalized:

            return None

        return self.registry.get(
            normalized,
        )

    def list_agents(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded_agents(
        self,
    ) -> list[str]:

        return self.registry.loaded()
