from __future__ import annotations

import logging
from typing import Callable

from core.execution_plan import ExecutionPlan

from core.context.base import BaseContextProvider

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

    - Resolver providers requeridos por ExecutionPlan.
    - Cargar información contextual.
    - Gestionar ciclo de vida de providers.
    - Aislar errores individuales.
    - Entregar contexto al sistema de ejecución.

    No:

    - Analiza intención.
    - Decide qué contexto usar.
    - Ejecuta skills.
    - Construye prompts.
    """

    def __init__(self):

        self.provider_factories: dict[
            str,
            Callable[[], BaseContextProvider],
        ] = {
            "project": ProjectProvider,
            "engram": EngramProvider,
            "memory": MemoryProvider,
            "obsidian": ObsidianProvider,
            "documents": DocumentsProvider,
            "gentleman": GentlemanProvider,
            "standards": StandardsProvider,
            "spec": SpecProvider,
        }

        self.providers: dict[
            str,
            BaseContextProvider,
        ] = {}

        self.metrics = {
            "providers_loaded": 0,
            "providers_failed": 0,
            "contexts_generated": 0,
        }

        self._context_cache: dict[str, dict] = {}

    # ==========================================================
    # Provider Normalization
    # ==========================================================

    def _normalize_provider(
        self,
        name: str,
    ) -> str:

        return ExecutionPlan.normalize_provider(name)

    # ==========================================================
    # Provider lifecycle
    # ==========================================================

    def _get_provider(
        self,
        name: str,
    ) -> BaseContextProvider | None:

        if name in self.providers:

            return self.providers[name]

        factory = self.provider_factories.get(name)

        if not factory:

            logger.warning(
                "Provider de contexto no registrado: %s",
                name,
            )

            return None

        try:

            provider = factory()

            self.providers[name] = provider

            self.metrics["providers_loaded"] += 1

            logger.info(
                "Context provider inicializado: %s",
                name,
            )

            return provider

        except Exception:

            self.metrics["providers_failed"] += 1

            logger.exception(
                "Error inicializando provider: %s",
                name,
            )

            return None

    # ==========================================================
    # Context generation
    # ==========================================================

    def build(
        self,
        plan: ExecutionPlan,
    ) -> dict:

        cache_key = plan.id

        if cache_key in self._context_cache:

            logger.debug(
                "Contexto recuperado desde cache: %s",
                cache_key,
            )

            return self._context_cache[cache_key]

        context: dict = {
            "query": plan.original_task,
            "execution_plan": plan.to_dict(),
        }

        requirements = list(dict.fromkeys(plan.context_requirements))

        invalid = plan.validate_context_requirements()

        if invalid:

            logger.warning(
                "Context providers inválidos detectados: %s",
                invalid,
            )

        for requirement in requirements:

            provider = self._get_provider(requirement)

            if provider is None:

                continue

            try:

                logger.info(
                    "Cargando contexto provider=%s",
                    requirement,
                )

                provider.load(
                    plan,
                    context,
                )

            except Exception:

                self.metrics["providers_failed"] += 1

                logger.exception(
                    "Falló carga de contexto provider=%s",
                    requirement,
                )

        self.metrics["contexts_generated"] += 1

        self._context_cache[cache_key] = context

        logger.info(
            "Contexto generado keys=%s",
            list(context.keys()),
        )

        return context

    # ==========================================================
    # Provider management
    # ==========================================================

    def register_provider(
        self,
        name: str,
        factory: Callable[
            [],
            BaseContextProvider,
        ],
    ) -> None:
        """
        Permite agregar providers dinámicamente.
        """

        self.provider_factories[name] = factory

    def clear_cache(
        self,
    ) -> None:

        self._context_cache.clear()

    def get_loaded_providers(
        self,
    ) -> list[str]:

        return list(self.providers.keys())

    def get_metrics(
        self,
    ) -> dict:

        return self.metrics.copy()
