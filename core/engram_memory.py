import json
import logging
import os
import re
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.config import Config

logger = logging.getLogger(__name__)


class EngramMemory:
    """
    Cliente para Engram v1.20+.

    Comandos CLI usados:
    - save <title> <msg> [--project NAME]
    - search <query> [--limit N] [--project NAME]
    - stats [--project NAME]
    - delete <obs_id> [--project NAME]

    Base de datos: ENGRAM_DATA_DIR (por defecto ~/.engram)
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        project: Optional[str] = None,
        async_save: bool = True,
    ):
        # Unificado con el directorio por defecto de Engram
        self.data_dir = data_dir or Path.home() / ".engram"
        self.project = project or Config.PROJECT_ROOT.name
        self.async_save = async_save

        os.environ["ENGRAM_DATA_DIR"] = str(self.data_dir)

        self._available = self._check_available()
        if not self._available:
            logger.warning(
                "Engram no está instalado o no se encuentra en el PATH. "
                "La memoria persistente estará desactivada. "
                "Instala con: brew install engram (o descarga el binario)."
            )
        else:
            logger.info(
                "Engram disponible. Data dir: %s | Project: %s", self.data_dir, self.project
            )

    def _check_available(self) -> bool:
        return shutil.which("engram") is not None

    def _run_command(self, cmd: List[str], timeout: int = 10) -> tuple[bool, str, str]:
        if not self._available:
            return False, "", "Engram no disponible"

        full_cmd = ["engram"] + cmd
        try:
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
            return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            logger.warning("Comando Engram agotó el tiempo de espera: %s", full_cmd)
            return False, "", "Timeout"
        except FileNotFoundError:
            logger.error("Binario Engram no encontrado")
            self._available = False
            return False, "", "Binario no encontrado"
        except Exception as e:
            logger.exception("Error ejecutando Engram: %s", e)
            return False, "", str(e)

    def save(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        source: str = "aiclient",
        async_mode: Optional[bool] = None,
    ) -> bool:
        if not content or not content.strip():
            return False
        if not self._available:
            return False

        use_async = async_mode if async_mode is not None else self.async_save

        if use_async:
            thread = threading.Thread(
                target=self._save_sync,
                args=(content, tags, source),
                daemon=True,
            )
            thread.start()
            return True
        else:
            return self._save_sync(content, tags, source)

    def _save_sync(
        self, content: str, tags: Optional[List[str]] = None, source: str = "aiclient"
    ) -> bool:
        # Título = primeras 50 caracteres
        title = content[:50].strip() + ("..." if len(content) > 50 else "")
        msg = content

        if tags:
            msg = f"[{', '.join(tags)}] {content}"

        cmd = ["save", title, msg, "--project", self.project]
        success, stdout, stderr = self._run_command(cmd)

        if not success:
            logger.debug("Error guardando memoria: %s", stderr or stdout)
        else:
            logger.debug("Memoria guardada: %s", title)
        return success

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Busca memorias en Engram v1.20 (salida en texto plano).

        Formato real de Engram:
        Found N memories:
        [1] #13 (manual) — Título corto
            Contenido de la memoria aquí
            2026-07-30 15:46:16 | project: aiclient | scope: project
        """
        if not query or not query.strip():
            return []
        if not self._available:
            return []

        cmd = ["search", query, "--limit", str(limit), "--project", self.project]
        success, stdout, stderr = self._run_command(cmd, timeout=15)

        if not success or not stdout:
            logger.debug("Error o sin resultados en search: %s", stderr)
            return []

        results: List[Dict[str, Any]] = []
        current: Optional[Dict[str, Any]] = None

        for raw_line in stdout.splitlines():
            line = raw_line.rstrip()

            header = re.match(
                r"^\[(\d+)\]\s+#(\d+)\s+\(([^)]+)\)\s+[—\-]\s+(.*)$",
                line,
            )
            if header:
                if current:
                    results.append(current)

                current = {
                    "id": header.group(2),
                    "index": int(header.group(1)),
                    "type": header.group(3),
                    "title": header.group(4).strip(),
                    "content": "",
                    "score": 0.0,
                }
                continue

            if current is None:
                continue

            stripped = line.strip()
            if not stripped:
                continue

            if re.match(r"^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}", stripped):
                continue
            if "project:" in stripped and "scope:" in stripped:
                continue

            if current["content"]:
                current["content"] += " " + stripped
            else:
                current["content"] = stripped

        if current:
            results.append(current)

        for r in results:
            if not r.get("content"):
                r["content"] = r.get("title", "")

        return results[:limit]

    def get_context(self, query: str, limit: int = 5) -> str:
        """Recupera memorias y las formatea para inyectarlas en un prompt."""
        memories = self.recall(query, limit=limit)
        if not memories:
            return ""

        memories = sorted(memories, key=lambda x: x.get("id", 0), reverse=True)

        lines = ["=== MEMORIA RECUPERADA (Engram) ==="]
        for m in memories:
            content = m.get("content") or m.get("title") or ""
            if len(content) > 500:
                content = content[:497] + "..."
            lines.append(f"- {content}")
        return "\n".join(lines)

    def stats(self) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None

        cmd = ["stats", "--project", self.project]
        success, stdout, _ = self._run_command(cmd)
        if not success or not stdout:
            return None

        stats: Dict[str, Any] = {}
        for line in stdout.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                stats[key.strip()] = val.strip()
        return stats

    def forget(self, memory_id: str) -> bool:
        if not self._available:
            return False

        cmd = ["delete", memory_id, "--project", self.project]
        success, _, _ = self._run_command(cmd)
        return success

    def is_available(self) -> bool:
        return self._available
