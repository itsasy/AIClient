from core.project_inspector import ProjectInspector
from core.engram_memory import EngramMemory
from core.document_ingestor import DocumentIngestor


class ContextBuilder:
    """
    Construye el contexto para el orquestador.
    No inspecciona proyecto ni activa RAG en consultas triviales.
    """

    def __init__(self):
        self._rag = None
        self.inspector = ProjectInspector()
        self.engram = EngramMemory()
        self.ingestor = DocumentIngestor()

    @property
    def rag(self):
        """Lazy load: aquí aparecen los weights de HF la primera vez."""
        if self._rag is None:
            from obsidian.rag import RAG

            self._rag = RAG()
        return self._rag

    def _is_trivial(self, query: str) -> bool:
        t = query.strip().lower()
        trivial_phrases = {
            "hola",
            "hi",
            "hello",
            "hey",
            "buenas",
            "buenos días",
            "buenos dias",
            "qué tal",
            "que tal",
            "gracias",
            "ok",
            "vale",
            "adios",
            "adiós",
            "chao",
            "¿cómo estás?",
            "como estas",
            "cómo estás",
        }
        if t in trivial_phrases:
            return True

        code_keywords = {
            "proyecto",
            "código",
            "codigo",
            "archivo",
            "función",
            "funcion",
            "clase",
            "script",
            "endpoint",
            "repo",
            "api",
            "docker",
            "composer",
            "laravel",
            "react",
            "vue",
            "django",
            "refactor",
            "migra",
            "spec",
        }
        if any(k in t for k in code_keywords):
            return False

        words = t.split()
        if len(words) < 6:
            memory_keywords = {"mi", "color", "favorito", "preferido", "recuerdas", "memoria"}
            if any(k in t for k in memory_keywords):
                return False
            return True
        return False

    def _wants_obsidian(self, query: str) -> bool:
        q = query.lower()
        keys = [
            "busca",
            "encuentra",
            "en mis notas",
            "obsidian",
            "segunda mente",
            "segundo cerebro",
        ]
        return any(k in q for k in keys)

    def build(self, query: str) -> dict:
        if self._is_trivial(query):
            return {"query": query}

        project = self.inspector.inspect()

        obsidian_context = ""
        if self._wants_obsidian(query):
            obsidian_context = self.rag.get_relevant_context(query)

        context = {
            "project": project,
            "obsidian": obsidian_context,
            "query": query,
        }

        # Engram lo inyecta el Orchestrator (evitar duplicar)
        return context

    def get_ingested_docs(self) -> list:
        return self.ingestor.list_ingested()
