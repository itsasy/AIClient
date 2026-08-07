from __future__ import annotations

import logging

from typing import Any

from core.context.registry import ContextRegistry

from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Gestiona carga y composición de contexto.

    Responsabilidades:

    - Resolver providers.
    - Ejecutar carga contextual.
    - Componer execution_context.
    - Adjuntar contexto al plan.

    No:

    - Ejecuta tareas.
    - Ejecuta agentes.
    - Ejecuta skills.
    - Modifica intención.
    - Decide estrategia LLM.
    """

    def __init__(
        self,
        registry: ContextRegistry | None = None,
    ) -> None:

        self.registry = registry or ContextRegistry()

    # ==================================================
    # Public API
    # ==================================================

    def build(
        self,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:

        context: dict[str, Any] = {}

        for requirement in plan.context_requirements:

            provider = self.registry.get(
                requirement,
            )

            if not provider:

                logger.warning(
                    "Context provider no encontrado=%s",
                    requirement,
                )

                continue

            try:

                data = provider.load(
                    plan,
                    context,
                )

                if data:

                    context.update(
                        data,
                    )

            except Exception as exc:

                logger.exception(
                    "Error cargando context provider=%s",
                    requirement,
                )

                context[requirement] = {
                    "error": str(exc),
                }

        return context

    # ==================================================
    # Execution integration
    # ==================================================

    def attach_to_plan(
        self,
        plan: ExecutionPlan,
    ) -> dict[str, Any]:

        context = self.build(
            plan,
        )

        plan.loaded_context = context

        plan.execution_context.update(
            context,
        )

        return context

    # ==================================================
    # Provider management
    # ==================================================

    def register(
        self,
        provider,
        aliases: list[str] | None = None,
        overwrite: bool = False,
    ) -> None:

        self.registry.register(
            provider,
            aliases=aliases,
            overwrite=overwrite,
        )

    def available_providers(
        self,
    ) -> list[str]:

        return self.registry.list()

    # ==================================================
    # Inspection
    # ==================================================

    def describe(
        self,
    ) -> dict[str, Any]:

        return {
            "providers": self.registry.list(),
            "aliases": self.registry.aliases(),
        }
