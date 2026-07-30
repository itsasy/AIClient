import json
import logging
import shutil
import subprocess
import threading
from typing import Optional, List, Dict, Any

from core.config import Config

logger = logging.getLogger(__name__)


class EngramMemory:
    """
    Cliente para Engram v1.20.0 – Memoria persistente para AIClient.
    Compatible con salida en texto (no JSON) de `engram stats` y `engram search`.
    """

    def __init__(
        self,
        project: str = "aiclient",
        async_save: bool = True,
    ):
        self.project = project
        self.async_save = async_save

        self._available = self._check_available()
        if not self._available:
            logger.warning(
                "Engram no está instalado o no se encuentra en el PATH. "
                "La memoria persistente estará desactivada."
            )
        else:
            logger.info("Engram disponible")

    def _check_available(self) -> bool:
        return shutil.which("engram") is not None

    def _run_command(
        self,
        cmd: List[str],
        timeout: int = 10,
    ) -> tuple[bool, str, str]:
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
            return (
                result.returncode == 0,
                result.stdout.strip(),
                result.stderr.strip(),
            )
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

        words = content.split()
        title = " ".join(words[:6]) if words else "memory"
        if len(title) > 60:
            title = title[:57] + "..."

        if use_async:
            thread = threading.Thread(
                target=self._save_sync,
                args=(title, content, tags, source),
                daemon=True,
            )
            thread.start()
            logger.debug("Memoria encolada: %s", title)
            return True
        else:
            return self._save_sync(title, content, tags, source)

    def _save_sync(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        source: str = "aiclient",
    ) -> bool:
        cmd = ["save", title, content, "--project", self.project]

        if tags:
            cmd.extend(["--tags", ",".join(tags)])
        if source and source not in (tags or []):
            cmd.extend(["--tags", source])

        success, stdout, stderr = self._run_command(cmd, timeout=15)
        if not success:
            logger.debug("Error guardando: %s", stderr or stdout)
        else:
            logger.debug("Guardado: %s", title)
        return success

    def recall(
        self,
        query: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not query or not query.strip():
            return []

        if not self._available:
            return []

        cmd = [
            "search",
            query,
            "--project",
            self.project,
            "--limit",
            str(limit),
        ]

        success, stdout, stderr = self._run_command(cmd, timeout=15)
        if not success or not stdout:
            logger.debug("Error o sin resultados: %s", stderr)
            return []

        if "No memories found" in stdout:
            return []

        results = []
        current = {}
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("ID:"):
                if current:
                    results.append(current)
                    current = {}
                current["id"] = line.replace("ID:", "").strip()
            elif line.startswith("Title:"):
                current["title"] = line.replace("Title:", "").strip()
            elif line.startswith("Content:"):
                current["content"] = line.replace("Content:", "").strip()
            elif line.startswith("Score:"):
                try:
                    current["score"] = float(line.replace("Score:", "").strip())
                except ValueError:
                    current["score"] = 0.0
        if current:
            results.append(current)

        return results

    def get_context(self, query: str, limit: int = 5) -> str:
        memories = self.recall(query, limit=limit)
        if not memories:
            return ""

        lines = ["=== MEMORIA RECUPERADA (Engram) ==="]
        for m in memories:
            content = m.get("content") or m.get("title", "")
            if not content:
                continue
            if len(content) > 500:
                content = content[:497] + "..."
            lines.append(f"- {content}")
        return "\n".join(lines)

    def stats(self) -> Optional[Dict[str, Any]]:
        if not self._available:
            return None

        success, stdout, _ = self._run_command(["stats"], timeout=10)
        if not success or not stdout:
            return None

        stats = {}
        for line in stdout.splitlines():
            line = line.strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip().lower().replace(" ", "_")
                value = value.strip()
                if value.isdigit():
                    value = int(value)
                elif value == "none yet":
                    value = 0
                stats[key] = value

        # Compatibilidad
        if "observations" in stats:
            stats["total_memories"] = stats["observations"]
        if "sessions" in stats:
            stats["total_sessions"] = stats["sessions"]

        return stats

    def forget(self, memory_id: str) -> bool:
        if not self._available:
            return False
        # `delete` no soporta --project, pero el ID es global
        success, _, _ = self._run_command(["delete", memory_id], timeout=10)
        return success

    def is_available(self) -> bool:
        return self._available
