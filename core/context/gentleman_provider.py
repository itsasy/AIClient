import logging
from typing import Any

from core.gentleman_skills import GentlemanSkills
from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class GentlemanProvider(BaseContextProvider):
    """
    Proveedor de Gentleman Skills.

    Carga conocimiento operativo relevante
    para el ExecutionPlan actual.

    Responsabilidades:

    - Buscar skills relacionadas con la tarea.
    - Entregar contenido + metadata.
    - Mantener contexto estructurado.

    No:

    - Decide prioridades.
    - Ejecuta skills.
    - Construye prompts.
    """

    key = "gentleman"

    def __init__(self):

        self.skills = GentlemanSkills()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:
        relevant = self.skills.find_relevant(
            query=plan.original_task,
            limit=5,
        )

        if not relevant:

            logger.debug("No se encontraron Gentleman Skills relevantes.")

            return

        loaded = {}

        for name in relevant:

            content = self.skills.get_skill(name)

            if not content:

                continue

            metadata = self.skills.get_metadata(name)

            loaded[name] = {
                "content": content,
                "metadata": metadata or {},
            }

        if not loaded:

            return

        context[self.key] = loaded

        logger.info(
            "Gentleman skills cargadas: %s",
            list(loaded.keys()),
        )
