from __future__ import annotations

import logging

from core.execution_plan import ExecutionPlan

from core.context.base import BaseContextProvider
from core.context.registry import ContextRegistry


from core.context.project_provider import ProjectProvider
from core.context.engram_provider import EngramProvider
from core.context.memory_provider import MemoryProvider
from core.context.obsidian_provider import ObsidianProvider
from core.context.documents_provider import DocumentsProvider
from core.context.gentleman_provider import GentlemanProvider
from core.context.standards_provider import StandardsProvider
from core.context.spec_provider import SpecProvider

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Constructor de contexto.

    Responsabilidades:

    - Resolver providers.
    - Construir contexto.
    - Gestionar cache.

    No:

    - Ejecuta agentes.
    - Ejecuta skills.
    - Decide planes.
    """

    def __init__(
        self,
        registry: ContextRegistry | None = None,
    ):

        self.registry = registry or ContextRegistry()

        self.metrics = {
            "providers_loaded": 0,
            "providers_failed": 0,
            "contexts_generated": 0,
        }

        self._context_cache: dict[
            str,
            dict,
        ] = {}

        self._register_defaults()

    # ==================================================
    # Defaults
    # ==================================================

    def _register_defaults(
        self,
    ) -> None:

        providers = [
            ProjectProvider,
            MemoryProvider,
            EngramProvider,
            DocumentsProvider,
            GentlemanProvider,
            StandardsProvider,
            SpecProvider,
            ObsidianProvider,
        ]

        for provider in providers:

            try:

                self.registry.register(provider)

            except ValueError:

                pass

    # ==================================================
    # Build
    # ==================================================

    def build(
        self,
        plan: ExecutionPlan,
    ) -> dict:

        if plan.id in self._context_cache:

            return self._context_cache[plan.id]

        context = {
            "query": plan.original_task,
            "execution_plan": plan.to_dict(),
        }

        for requirement in dict.fromkeys(plan.context_requirements):

            provider = self.registry.get(requirement)

            if provider is None:

                self.metrics["providers_failed"] += 1

                logger.warning(
                    "Provider no encontrado=%s",
                    requirement,
                )

                continue

            try:

                provider.load(
                    plan,
                    context,
                )

                self.metrics["providers_loaded"] += 1

            except Exception:

                self.metrics["providers_failed"] += 1

                logger.exception(
                    "Error provider=%s",
                    requirement,
                )

        self.metrics["contexts_generated"] += 1

        self._context_cache[plan.id] = context

        return context

    # ==================================================
    # Management
    # ==================================================

    def register_provider(
        self,
        provider: type[BaseContextProvider],
    ):

        self.registry.register(provider)

    def clear_cache(
        self,
    ):

        self._context_cache.clear()

    def providers(
        self,
    ) -> list[str]:

        return self.registry.list()

    def get_metrics(
        self,
    ) -> dict:

        return self.metrics.copy()
