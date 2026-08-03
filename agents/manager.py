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

    def delegate(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any] | None = None,
    ) -> Any:

        context = context or {}

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

        return agent.process(
            plan,
            context,
        )

    def _select(
        self,
        plan: ExecutionPlan,
    ) -> Agent | None:

        if plan.agent:

            agent = self.registry.get(
                plan.agent,
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

    def get(
        self,
        name: str,
    ) -> Agent | None:

        return self._get_agent(name)

    def list_agents(
        self,
    ) -> list[str]:

        return self.registry.list()

    def loaded_agents(
        self,
    ) -> list[str]:

        return self.registry.loaded()
