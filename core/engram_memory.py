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
    Cliente para Engram v1.20.0+ – memoria persistente para AIClient.

    Utiliza el CLI de Engram con los nuevos comandos:
    - save <title> <msg>
    - search <query>
    - stats
    - delete <obs_id>

    Todas las memorias se guardan con --project aiclient para aislarlas.
    """

    def __init__(
        self,
        project: str = "aiclient",
        async_save: bool = True,
    ):
        self.project = project
        self.async_save = async_save

        # Verificar si Engram está disponible
        self._available = self._check_available()
        if not self._available:
            logger.warning(
                "Engram no está instalado o no se encuentra en el PATH. "
                "La memoria persistente estará desactivada. "
                "Instala con: brew install engram (o descarga el binario)."
            )
        else:
            logger.info("Engram disponible en: %s", shutil.which("engram"))

    def _check_available(self) -> bool:
        return shutil.which("engram") is not None

    def _run_command(
        self,
        cmd: List[str],
        timeout: int = 10,
    ) -> tuple[bool, str, str]:
        """
        Ejecuta un comando de Engram de forma segura.
        """
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
        """
        Guarda una memoria usando `engram save`.

        Args:
            content: Contenido de la memoria.
            tags: Lista de etiquetas (se añaden como --tags).
            source: Fuente (se añade al contenido o como tag).
            async_mode: Si es True, ejecuta en hilo separado.

        Returns:
            bool: True si se guardó correctamente (o se encoló).
        """
        if not content or not content.strip():
            return False

        if not self._available:
            return False

        use_async = async_mode if async_mode is not None else self.async_save

        # Preparar título (primeras palabras) y mensaje (contenido)
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
        """Implementación síncrona con `engram save`."""
        cmd = ["save", title, content, "--project", self.project]

        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        # Añadir source como tag si no está ya
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
        """
        Busca memorias usando `engram search`.

        Args:
            query: Texto a buscar.
            limit: Número máximo de resultados.

        Returns:
            Lista de memorias con campos: id, title, content, score, etc.
        """
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
            "--json",
        ]

        success, stdout, stderr = self._run_command(cmd, timeout=15)
        if not success or not stdout:
            logger.debug("Error o sin resultados: %s", stderr)
            return []

        try:
            data = json.loads(stdout)
            # La salida puede ser una lista directamente o un objeto con "results"
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError as e:
            logger.warning("Error parseando JSON: %s", e)
            return []

    def get_context(self, query: str, limit: int = 5) -> str:
        """
        Recupera memorias y las formatea para inyectarlas en un prompt.
        """
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
        """
        Obtiene estadísticas con `engram stats`.
        """
        if not self._available:
            return None

        # stats no soporta --project, devuelve globales
        success, stdout, _ = self._run_command(["stats", "--json"], timeout=10)
        if not success or not stdout:
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None

    def forget(self, memory_id: str) -> bool:
        """
        Elimina una memoria con `engram delete`.
        """
        if not self._available:
            return False

        # delete no soporta --project, elimina por ID global
        success, _, _ = self._run_command(["delete", memory_id], timeout=10)
        return success

    def is_available(self) -> bool:
        return self._available
