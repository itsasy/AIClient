from pathlib import Path
from core.config import Config
from obsidian.index import ObsidianIndex
from obsidian.semantic import SemanticIndex


class ObsidianSearch:
    def __init__(self):
        self.vault_path = Path(Config.OBSIDIAN_VAULT_PATH).expanduser()
        self.fts_index = ObsidianIndex()
        self.semantic_index = SemanticIndex()

    def search(self, query: str, max_results: int = 5, alpha: float = 0.5):
        """
        Búsqueda híbrida: combina FTS5 y semántica.
        alpha: ponderación entre FTS (1-alpha) y semántica (alpha).
        """
        if not self.vault_path.exists():
            return []

        # 1. Obtener resultados de FTS (contenido completo)
        fts_results = self.fts_index.search(query, max_results=max_results * 2)

        # 2. Obtener resultados semánticos (solo paths y scores)
        semantic_results = self.semantic_index.search(query, top_k=max_results * 2)

        # 3. Fusionar resultados con puntuación combinada
        combined = {}
        for r in fts_results:
            score_fts = -r["rank"]  # rank es negativo para mejores resultados
            combined[r["path"]] = {
                "path": r["path"],
                "score_fts": score_fts,
                "score_semantic": 0.0,
                "snippet": r.get("snippet", ""),
                "content": r.get("content", ""),
            }

        for r in semantic_results:
            path = r["path"]
            if path in combined:
                combined[path]["score_semantic"] = r["score"]
            else:
                # Si solo aparece en semántica, asignamos score_fts = 0
                combined[path] = {
                    "path": path,
                    "score_fts": 0.0,
                    "score_semantic": r["score"],
                    "snippet": "",
                    "content": "",  # Se rellenará después si es necesario
                }

        # 4. Normalizar y calcular puntuación final (ponderada)
        max_fts = max([d["score_fts"] for d in combined.values()], default=1)
        max_sem = max([d["score_semantic"] for d in combined.values()], default=1)

        for path, data in combined.items():
            norm_fts = data["score_fts"] / max_fts if max_fts > 0 else 0
            norm_sem = data["score_semantic"] / max_sem if max_sem > 0 else 0
            data["final_score"] = (1 - alpha) * norm_fts + alpha * norm_sem

        # 5. Ordenar y limitar
        sorted_items = sorted(
            combined.values(), key=lambda x: x["final_score"], reverse=True
        )
        top_results = sorted_items[:max_results]

        # 6. Rellenar contenido para los que faltan (por si solo aparecen en semántica)
        for r in top_results:
            if not r["content"] and r["path"]:
                # Recuperar contenido del archivo
                try:
                    filepath = self.vault_path / r["path"]
                    if filepath.exists():
                        r["content"] = filepath.read_text(
                            encoding="utf-8", errors="ignore"
                        )[:1200]
                except Exception:
                    pass

        return top_results

    def build_context(self, query: str) -> str:
        results = self.search(query)
        if not results:
            return ""

        context = "=== CONOCIMIENTO RELEVANTE (RAG HÍBRIDO) ===\n\n"
        for r in results:
            context += f"📄 {r['path']}\n{r['content'][:1000]}\n{'─' * 80}\n\n"
        return context
