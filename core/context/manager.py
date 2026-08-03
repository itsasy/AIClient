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
    Construye el contexto requerido por un ExecutionPlan.

    Características:

    - Providers lazy.
    - Providers independientes.
    - Fallo aislado por provider.
    - Contexto extensible.

    No:

    - Decide qué contexto necesita el plan.
    - Analiza intención.
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
            "spec": SpecProvider,
            "standards": StandardsProvider,
            "gentleman": GentlemanProvider,
        }

        self.providers: dict[
            str,
            BaseContextProvider,
        ] = {}

        self.metrics = {
            "loaded": 0,
            "failed": 0,
        }

    # ==========================================================
    # Provider lifecycle
    # ==========================================================

    def _get_provider(
        self,
        key: str,
    ) -> BaseContextProvider | None:

        if key in self.providers:

            return self.providers[key]

        factory = self.provider_factories.get(key)

        if factory is None:

            logger.warning(
                "Context provider no registrado: %s",
                key,
            )

            return None

        try:

            provider = factory()

            self.providers[key] = provider

            return provider

        except Exception:

            self.metrics["failed"] += 1

            logger.exception(
                "No se pudo inicializar provider: %s",
                key,
            )

            return None

    # ==========================================================
    # Context building
    # ==========================================================

    def build(
        self,
        plan: ExecutionPlan,
    ) -> dict:

        context = {
            "query": plan.original_task,
        }

        requirements = list(dict.fromkeys(plan.context_requirements or []))

        invalid = plan.validate_context_requirements()

        if invalid:

            logger.warning(
                "Context providers inválidos: %s",
                invalid,
            )

        for requirement in requirements:

            provider = self._get_provider(requirement)

            if provider is None:

                continue

            try:

                logger.info(
                    "Cargando contexto: %s",
                    requirement,
                )

                provider.load(
                    plan,
                    context,
                )

                self.metrics["loaded"] += 1

            except Exception:

                self.metrics["failed"] += 1

                logger.exception(
                    "Error cargando contexto provider=%s",
                    requirement,
                )

        logger.info(
            "Contexto construido: %s",
            list(context.keys()),
        )

        return context

    # ==========================================================
    # Management
    # ==========================================================

    def register_provider(
        self,
        key: str,
        factory: Callable[
            [],
            BaseContextProvider,
        ],
    ) -> None:
        """
        Permite agregar providers externos
        sin modificar la clase.
        """

        self.provider_factories[key] = factory

    def get_loaded_providers(
        self,
    ) -> list[str]:

        return list(self.providers.keys())

    def get_metrics(
        self,
    ) -> dict:

        return self.metrics.copy()
