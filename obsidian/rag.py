import logging
from core.config import Config

logger = logging.getLogger(__name__)


class RAG:
    def __init__(self):
        self._search = None

    def _get_search(self):
        """Inicializa ObsidianSearch solo si el vault existe."""
        if self._search is None:
            if Config.OBSIDIAN_VAULT_PATH.exists():
                from obsidian.search import ObsidianSearch

                self._search = ObsidianSearch()
            else:
                self._search = False
        return self._search if self._search is not False else None

    def get_relevant_context(self, query: str, max_results: int = 8) -> str:
        """
        Obtiene contexto relevante de Obsidian mediante búsqueda híbrida.
        Si falla, devuelve un mensaje de error informativo.
        """
        search = self._get_search()
        if not search:
            return ""

        try:
            results = search.search(query, max_results=max_results)
        except Exception as e:
            logger.warning("Error al buscar en Obsidian: %s", e)
            return "No se pudo obtener contexto de Obsidian (error interno).\n"

        if not results:
            return "No se encontró información relevante en Obsidian.\n"

        context_lines = [
            "=== CONOCIMIENTO RELEVANTE (RAG HÍBRIDO) ===",
            "Búsqueda combinada: FTS5 + semántica (modelo all-MiniLM-L6-v2)",
            "",
        ]

        for r in results:
            snippet = r.get("snippet", "")
            content = r.get("content", "")
            score = r.get("final_score", r.get("score", 0))
            display_content = snippet if snippet else content[:800]

            context_lines.append(f"📄 {r['path']} (relevancia: {score:.3f})")
            context_lines.append(display_content)
            context_lines.append("─" * 80)
            context_lines.append("")

        return "\n".join(context_lines)
