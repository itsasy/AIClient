import hashlib
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

from core.config import Config


class ObsidianIndex:
    DB_PATH = Config.PROJECT_ROOT / ".obsidian_cache.db"

    def __init__(self):
        self.vault_path = Config.OBSIDIAN_VAULT_PATH.expanduser()
        self._init_db()

    def _init_db(self):
        """Crea la tabla FTS5 si no existe."""
        with sqlite3.connect(str(self.DB_PATH)) as conn:
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS files_fts
                USING fts5(path, content, mtime, tokenize='porter unicode61')
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            conn.commit()

    def _get_file_mtime(self, filepath: Path) -> str:
        return str(filepath.stat().st_mtime)

    def _compute_file_hash(self, filepath: Path) -> str:
        hasher = hashlib.md5()
        try:
            hasher.update(filepath.read_bytes())
        except OSError:
            pass
        return hasher.hexdigest()

    def sync(self):
        """Sincroniza el índice con el vault: añade, actualiza o elimina archivos."""
        if not self.vault_path.exists():
            return

        # Obtener todos los archivos .md
        current_files = {}
        for md_file in self.vault_path.rglob("*.md"):
            rel_path = str(md_file.relative_to(self.vault_path))
            current_files[rel_path] = md_file

        with sqlite3.connect(str(self.DB_PATH)) as conn:
            # Obtener archivos indexados
            indexed_rows = conn.execute("SELECT path, mtime FROM files_fts").fetchall()
            indexed_files = {row[0]: row[1] for row in indexed_rows}

            # Archivos a añadir o actualizar
            for rel_path, md_file in current_files.items():
                new_mtime = self._get_file_mtime(md_file)
                if (
                    rel_path not in indexed_files
                    or indexed_files[rel_path] != new_mtime
                ):
                    content = md_file.read_text(encoding="utf-8", errors="ignore")
                    conn.execute(
                        "INSERT OR REPLACE INTO files_fts (path, content, mtime) VALUES (?, ?, ?)",
                        (rel_path, content, new_mtime),
                    )

            # Archivos a eliminar
            for rel_path in indexed_files:
                if rel_path not in current_files:
                    conn.execute("DELETE FROM files_fts WHERE path = ?", (rel_path,))

            conn.commit()

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Busca en el índice FTS5 y devuelve fragmentos relevantes."""
        self.sync()

        if not query or not query.strip():
            return []

        with sqlite3.connect(str(self.DB_PATH)) as conn:
            conn.row_factory = sqlite3.Row

            # Escapar comillas simples para la consulta FTS
            clean_query = query.replace("'", "''")

            # Usar búsqueda FTS con ranking BM25
            sql = """
                SELECT
                    path,
                    snippet(files_fts, 1, '<mark>', '</mark>', '...', 30) as snippet,
                    rank
                FROM files_fts
                WHERE files_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            rows = conn.execute(sql, (clean_query, max_results)).fetchall()

            results = []
            for row in rows:
                # Obtener contenido completo para el contexto (opcional)
                full_content = conn.execute(
                    "SELECT content FROM files_fts WHERE path = ?", (row["path"],)
                ).fetchone()
                results.append(
                    {
                        "path": row["path"],
                        "snippet": row["snippet"],
                        "content": full_content["content"] if full_content else "",
                        "score": -row["rank"],  # rank es menor = mejor
                    }
                )
            return results
