import logging

from core.execution_plan import ExecutionPlan

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
    Construye el contexto necesario para un ExecutionPlan.

    Cada provider es independiente y solamente modifica
    la sección de contexto que le corresponde.

    La selección de providers se realiza mediante:
        plan.context_requirements
    """

    def __init__(self):

        providers = [
            ProjectProvider(),
            EngramProvider(),
            MemoryProvider(),
            ObsidianProvider(),
            DocumentsProvider(),
            SpecProvider(),
            StandardsProvider(),
            GentlemanProvider(),
        ]

        self.providers = {provider.key: provider for provider in providers}

    def build(
        self,
        plan: ExecutionPlan,
    ) -> dict:

        context = {
            "query": plan.original_task,
        }

        invalid = plan.validate_context_requirements()

        if invalid:

            logger.warning(
                "Context providers inválidos: %s",
                invalid,
            )

        for requirement in plan.context_requirements:

            provider = self.providers.get(requirement)

            if provider is None:

                logger.warning(
                    "Context provider no registrado: %s",
                    requirement,
                )

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

            except Exception:

                logger.exception(
                    "Error cargando contexto: %s",
                    requirement,
                )

        logger.info(
            "Contexto construido: %s",
            list(context.keys()),
        )

        return context
