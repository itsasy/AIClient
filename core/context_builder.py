from core.project_inspector import ProjectInspector
from core.engram_memory import EngramMemory
from core.document_ingestor import DocumentIngestor


class ContextBuilder:
    """
    Construye el contexto para el orquestador.
    Ahora evita inspeccionar el proyecto en consultas triviales o de memoria.
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
            memory_keywords = {"color", "favorito", "preferido", "recuerdas", "memoria", "olvidé"}
            if any(k in t for k in memory_keywords):
                return False
            return True
        return False

    def _wants_memory(self, query: str) -> bool:
        """Detecta si la consulta es puramente sobre memoria (no necesita proyecto/obsidian)."""
        q = query.lower()
        keys = {
            "color",
            "favorito",
            "preferido",
            "recuerdas",
            "memoria",
            "qué prefiero",
            "que prefiero",
            "olvidé",
            "dónde está",
        }
        return any(k in q for k in keys)

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
        # 1. Si es trivial o solo consulta de memoria → contexto mínimo
        if self._is_trivial(query) or self._wants_memory(query):
            return {"query": query}

        # 2. Consulta de código / proyecto → inspeccionar
        project = self.inspector.inspect()

        # 3. Obsidian solo si se pide explícitamente
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
