from __future__ import annotations

import logging
from typing import Callable

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
    Orquestador de contexto.

    Responsabilidades:

    - Resolver providers.
    - Construir contexto.
    - Gestionar cache.

    No:

    - Ejecuta Skills.
    - Ejecuta Agents.
    - Decide planes.
    """

    def __init__(
        self,
        registry: ContextRegistry | None = None,
    ):

        self.registry = registry or ContextRegistry()

        self._register_defaults()

        self.providers: dict[
            str,
            BaseContextProvider,
        ] = {}

        self.metrics = {
            "providers_loaded": 0,
            "providers_failed": 0,
            "contexts_generated": 0,
        }

        self._context_cache: dict[
            str,
            dict,
        ] = {}

    # ======================================================
    # Defaults
    # ======================================================

    def _register_defaults(
        self,
    ):

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

            self.registry.register(
                provider,
            )

    # ======================================================
    # Provider resolution
    # ======================================================

    def _get_provider(
        self,
        name: str,
    ) -> BaseContextProvider | None:

        if name in self.providers:

            return self.providers[name]

        provider = self.registry.get(
            name,
        )

        if provider is None:

            logger.warning(
                "Provider no encontrado=%s",
                name,
            )

            self.metrics["providers_failed"] += 1

            return None

        self.providers[name] = provider

        self.metrics["providers_loaded"] += 1

        return provider

    # ======================================================
    # Context generation
    # ======================================================

    def build(
        self,
        plan: ExecutionPlan,
    ) -> dict:

        cache_key = plan.id

        if cache_key in self._context_cache:

            return self._context_cache[cache_key]

        context: dict = {
            "query": plan.original_task,
            "execution_plan": plan.to_dict(),
        }

        requirements = list(
            dict.fromkeys(
                plan.context_requirements,
            )
        )

        for requirement in requirements:

            provider = self._get_provider(
                requirement,
            )

            if provider is None:
                continue

            try:

                provider.load(
                    plan,
                    context,
                )

            except Exception:

                self.metrics["providers_failed"] += 1

                logger.exception(
                    "Error provider=%s",
                    requirement,
                )

        self.metrics["contexts_generated"] += 1

        self._context_cache[cache_key] = context

        return context

    # ======================================================
    # Management
    # ======================================================

    def register_provider(
        self,
        provider: type[BaseContextProvider],
    ):

        self.registry.register(
            provider,
        )

    def clear_cache(
        self,
    ):

        self._context_cache.clear()

    def get_loaded_providers(
        self,
    ) -> list[str]:

        return list(
            self.providers.keys(),
        )

    def get_metrics(
        self,
    ) -> dict:

        return self.metrics.copy()
