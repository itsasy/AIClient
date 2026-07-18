import hashlib
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.config import Config

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np

    SEMANTIC_AVAILABLE = True
except ImportError:
    SEMANTIC_AVAILABLE = False
    logger.warning("sentence-transformers no instalado. RAG semántico desactivado.")


class SemanticIndex:
    CACHE_FILE = Config.PROJECT_ROOT / ".semantic_cache.pkl"
    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self):
        self.vault_path = Config.OBSIDIAN_VAULT_PATH.expanduser()
        self.vectors = []
        self.metadata = []
        self.model = None
        self._loaded = False

        if SEMANTIC_AVAILABLE:
            self._load_or_build()

    def _load_or_build(self):
        """Carga el índice del caché o lo reconstruye si falta o está obsoleto."""
        if self.CACHE_FILE.exists():
            try:
                with open(self.CACHE_FILE, "rb") as f:
                    data = pickle.load(f)
                if data.get("vault_path") == str(self.vault_path):
                    self.vectors = data["vectors"]
                    self.metadata = data["metadata"]
                    self._loaded = True
                    logger.info(
                        "Caché semántico cargado (%d documentos).", len(self.metadata)
                    )
                    return
            except Exception as e:
                logger.warning("Error cargando caché semántico: %s", e)

        self._build_index()

    def _build_index(self):
        """Construye el índice desde cero."""
        if not SEMANTIC_AVAILABLE:
            logger.warning(
                "No se puede construir índice semántico: dependencias faltantes."
            )
            return

        if not self.vault_path.exists():
            logger.warning("Vault de Obsidian no encontrado.")
            return

        logger.info("Construyendo índice semántico desde el vault...")
        self.model = SentenceTransformer(self.MODEL_NAME)

        texts = []
        metadata_list = []

        for md_file in self.vault_path.rglob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8", errors="ignore")[
                    :5000
                ]  # Limitamos longitud
                if content.strip():
                    rel_path = str(md_file.relative_to(self.vault_path))
                    texts.append(content)
                    metadata_list.append({"path": rel_path})
            except Exception as e:
                logger.debug("Error leyendo %s: %s", md_file, e)

        if not texts:
            logger.warning("No se encontraron archivos .md en el vault.")
            return

        # Generar embeddings por lotes (más eficiente)
        logger.info("Generando embeddings para %d documentos...", len(texts))
        self.vectors = self.model.encode(
            texts, show_progress_bar=True, convert_to_numpy=True
        )
        self.metadata = metadata_list
        self._loaded = True

        # Guardar caché
        self._save_cache()
        logger.info(
            "Índice semántico construido con %d documentos.", len(self.metadata)
        )

    def _save_cache(self):
        """Guarda el índice en disco."""
        try:
            data = {
                "vault_path": str(self.vault_path),
                "vectors": self.vectors,
                "metadata": self.metadata,
            }
            with open(self.CACHE_FILE, "wb") as f:
                pickle.dump(data, f)
            logger.debug("Caché semántico guardado en %s", self.CACHE_FILE)
        except Exception as e:
            logger.warning("Error guardando caché semántico: %s", e)

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Busca por similitud semántica."""
        if not self._loaded or not SEMANTIC_AVAILABLE:
            return []

        if not self.model:
            self.model = SentenceTransformer(self.MODEL_NAME)

        query_vec = self.model.encode([query], convert_to_numpy=True)[0]

        # Calcular similitud coseno con todos los vectores
        similarities = np.dot(self.vectors, query_vec) / (
            np.linalg.norm(self.vectors, axis=1) * np.linalg.norm(query_vec)
        )

        # Obtener top_k índices
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0.2:  # Umbral mínimo de relevancia
                results.append(
                    {
                        "path": self.metadata[idx]["path"],
                        "score": float(similarities[idx]),
                    }
                )
        return results
