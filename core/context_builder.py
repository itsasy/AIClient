from core.project_inspector import ProjectInspector
from core.engram_memory import EngramMemory
from core.document_ingestor import DocumentIngestor


class ContextBuilder:
    """
    Construye el contexto completo para el orquestador.

    Combina:
    - Proyecto (ProjectInspector)
    - Obsidian (RAG híbrido con FTS + semántica) -> Carga perezosa (lazy loading)
    - Memoria persistente (Engram)
    - Documentos ingeridos (metadatos y fragmentos relevantes)
    """

    def __init__(self):
        self._rag = None
        self.inspector = ProjectInspector()
        self.engram = EngramMemory()
        self.ingestor = DocumentIngestor()

    @property
    def rag(self):
        """Carga RAG solo cuando se accede a él (lazy loading)."""
        if self._rag is None:
            from obsidian.rag import RAG

            self._rag = RAG()
        return self._rag

    def build(self, query: str) -> dict:
        """
        Construye el diccionario de contexto para la consulta actual.
        Solo carga Obsidian si la consulta es relevante (largo > 3 palabras o keywords).
        """
        # 1. Proyecto (snapshot) - SIEMPRE
        project = self.inspector.inspect()

        # 2. Obsidian (RAG híbrido) - SOLO si la consulta lo merece
        obsidian_context = ""
        if len(query.split()) > 3 or any(
            k in query.lower() for k in ["busca", "encuentra", "en mis notas"]
        ):
            obsidian_context = self.rag.get_relevant_context(query)

        # 3. Memoria persistente (Engram)
        engram_context = self.engram.get_context(query)

        # 4. Documentos ingeridos (lista de metadatos)
        ingested_docs = self.ingestor.list_ingested()

        context = {
            "project": project,
            "obsidian": obsidian_context,
            "query": query,
        }

        if engram_context:
            context["engram"] = engram_context

        if ingested_docs:
            doc_list = "\n".join(
                [f"- {doc['name']} ({doc['chunks']} fragmentos)" for doc in ingested_docs]
            )
            context["ingested_docs"] = f"=== DOCUMENTOS INGERIDOS ===\n{doc_list}"

        return context

    def get_ingested_docs(self) -> list:
        """Devuelve la lista de documentos ingeridos."""
        return self.ingestor.list_ingested()
