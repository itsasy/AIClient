from typing import Any

from core.context.base import BaseContextProvider
from core.document_ingestor import DocumentIngestor
from core.execution_plan import ExecutionPlan


class DocumentsProvider(BaseContextProvider):

    key = "documents"

    def __init__(self) -> None:
        self.ingestor = DocumentIngestor()

    def load(
        self,
        plan: ExecutionPlan,
        context: dict[str, Any],
    ) -> dict[str, Any]:

        documents = self.ingestor.list_ingested()

        if not documents:
            return {}

        return {
            "documents": documents,
        }
