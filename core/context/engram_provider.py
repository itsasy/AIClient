from __future__ import annotations

import logging
from typing import Any

from core.context.base import BaseContextProvider
from core.engram_memory import EngramMemory
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class EngramProvider(BaseContextProvider):
    """
    Proveedor de memoria contextual de Engram.

    - Consulta memoria persistida.
    - No modifica el contexto acumulado.
    - Devuelve únicamente los datos propios del provider.
    """

    key = "engram"
    name = "Engram"
    description = "Memoria contextual persistida de Engram."

    def __init__(self) -> None:
        self.engram = EngramMemory()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        if not self.engram.is_available():
            logger.debug("Engram no disponible.")
            return {}

        memory = self.engram.get_context(
            query=plan.original_task,
            limit=5,
        )

        if not memory:
            return {}

        return {
            "memory": memory,
            "skills": [],
        }
