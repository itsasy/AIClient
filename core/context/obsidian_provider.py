from __future__ import annotations

import logging

from typing import Any

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ObsidianProvider(BaseContextProvider):

    key = "obsidian"

    def __init__(self):

        self.rag = None

        try:

            from obsidian.rag import RAG

            self.rag = RAG()

        except Exception:

            logger.warning("Obsidian RAG no disponible.")

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:

        if self.rag is None:

            return

        result = self.rag.get_relevant_context(
            plan.original_task,
        )

        if not result:

            return

        context[self.key] = result
