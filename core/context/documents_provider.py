from core.document_ingestor import DocumentIngestor

from core.context.provider import ContextProvider


class DocumentsProvider(ContextProvider):

    def __init__(self):

        self.ingestor = DocumentIngestor()

    def load(
        self,
        plan,
        context,
    ):

        if not plan.needs_documents:
            return

        context["documents"] = self.ingestor.list_ingested()
