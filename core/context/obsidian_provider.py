import logging
from typing import Any

from obsidian.rag import RAG

from core.context.base import BaseContextProvider
from core.execution_plan import ExecutionPlan

logger = logging.getLogger(__name__)


class ObsidianProvider(BaseContextProvider):

    key = "obsidian"

    def __init__(self):

        self.rag = RAG()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> None:

        result = self.rag.get_relevant_context(
            plan.original_task,
        )

        if not result:
            return

        context[self.key] = result
