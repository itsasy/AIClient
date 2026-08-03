from core.document_ingestor import DocumentIngestor
from core.context.base import BaseContextProvider


class DocumentsProvider(BaseContextProvider):

    key = "documents"

    def __init__(self):

        self.ingestor = DocumentIngestor()

    def load(
        self,
        plan,
        context,
    ) -> None:

        documents = self.ingestor.list_ingested()

        if not documents:
            return

        context[self.key] = documents
