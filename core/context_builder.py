from core.project_inspector import ProjectInspector
from obsidian.rag import RAG
from core.engram_memory import EngramMemory
from core.document_ingestor import DocumentIngestor


class ContextBuilder:
    """
    Construye el contexto completo para el orquestador.

    Combina:
    - Proyecto (ProjectInspector)
    - Obsidian (RAG híbrido con FTS + semántica)
    - Memoria persistente (Engram)
    - Documentos ingeridos (metadatos y fragmentos relevantes)
    """

    def __init__(self):
        self.rag = RAG()
        self.inspector = ProjectInspector()
        self.engram = EngramMemory()
        self.ingestor = DocumentIngestor()

    def build(self, query: str) -> dict:
        """
        Construye el diccionario de contexto para la consulta actual.

        Args:
            query (str): Consulta del usuario.

        Returns:
            dict: Diccionario con las claves:
                - project: Snapshot del proyecto (texto)
                - obsidian: Contexto relevante de Obsidian
                - engram: Memoria persistente recuperada (Engram)
                - ingested_docs: Lista de documentos ingeridos (metadatos)
                - query: La consulta original
        """
        # 1. Proyecto (snapshot)
        project = self.inspector.inspect()

        # 2. Obsidian (RAG híbrido)
        obsidian = self.rag.get_relevant_context(query)

        # 3. Memoria persistente (Engram)
        engram_context = self.engram.get_context(query)

        # 4. Documentos ingeridos (lista de metadatos)
        ingested_docs = self.ingestor.list_ingested()

        # Construir el contexto base
        context = {
            "project": project,
            "obsidian": obsidian,
            "query": query,
        }

        # Añadir Engram si hay resultados
        if engram_context:
            context["engram"] = engram_context

        # Añadir lista de documentos ingeridos (para que el asistente sepa qué tiene)
        if ingested_docs:
            # Formatear para el prompt
            doc_list = "\n".join(
                [
                    f"- {doc['name']} ({doc['chunks']} fragmentos)"
                    for doc in ingested_docs
                ]
            )
            context["ingested_docs"] = f"=== DOCUMENTOS INGERIDOS ===\n{doc_list}"

        return context

    def get_ingested_docs(self) -> list:
        """Devuelve la lista de documentos ingeridos (útil para comandos)."""
        return self.ingestor.list_ingested()
