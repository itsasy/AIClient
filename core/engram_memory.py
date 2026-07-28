import json
import logging
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.config import Config

logger = logging.getLogger(__name__)


class EngramMemory:
    """
    Cliente para Engram: memoria persistente para AIClient.

    Utiliza el CLI de Engram (subprocess) para guardar y recuperar memorias.
    Diseñado para ser tolerante a fallos: si Engram no está instalado,
    las operaciones fallan silenciosamente sin romper AIClient.

    Características:
    - Guardado asíncrono (no bloquea la respuesta).
    - Búsqueda con FTS5 (texto completo).
    - Formateo automático para inyección en prompts.
    - Estadísticas y gestión de memorias.
    """

    def __init__(
        self,
        db_path: Optional[Path] = None,
        binary: str = "engram",
        async_save: bool = True,
    ):
        """
        Inicializa el cliente de Engram.

        Args:
            db_path: Ruta al archivo SQLite de Engram.
                     Por defecto usa Config.ENGRAM_DB_PATH.
            binary: Nombre del binario de Engram (por defecto "engram").
            async_save: Si es True, guarda las memorias en un hilo separado.
        """
        self.binary = binary
        self.db_path = db_path or Config.ENGRAM_DB_PATH
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
            logger.info("Engram disponible en: %s", shutil.which(self.binary))

    # ============================================================
    # MÉTODOS PÚBLICOS
    # ============================================================

    def save(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        source: str = "aiclient",
        async_mode: Optional[bool] = None,
    ) -> bool:
        """
        Guarda una memoria en Engram.

        Args:
            content: Texto de la memoria.
            tags: Lista de etiquetas (ej. ["decision", "architecture"]).
            source: Fuente de la memoria (ej. "aiclient", "user").
            async_mode: Si es True, ejecuta en hilo separado.
                        Si es None, usa el valor de `self.async_save`.

        Returns:
            bool: True si se guardó correctamente (o se encoló para guardar).
        """
        if not content or not content.strip():
            return False

        if not self._available:
            return False

        use_async = async_mode if async_mode is not None else self.async_save

        if use_async:
            # Guardar en hilo separado para no bloquear
            thread = threading.Thread(
                target=self._save_sync,
                args=(content, tags, source),
                daemon=True,
            )
            thread.start()
            logger.debug("Memoria encolada para guardado asíncrono: %s", content[:50])
            return True
        else:
            return self._save_sync(content, tags, source)

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Busca memorias relevantes en Engram.

        Args:
            query: Texto de búsqueda.
            limit: Número máximo de resultados.

        Returns:
            Lista de memorias, cada una con al menos 'content' y 'id'.
            Si hay error, devuelve lista vacía.
        """
        if not query or not query.strip():
            return []

        if not self._available:
            return []

        cmd = [
            "recall",
            query,
            "--db",
            str(self.db_path),
            "--limit",
            str(limit),
            "--json",
        ]

        success, stdout, stderr = self._run_command(cmd, timeout=15)
        if not success or not stdout:
            logger.debug("Error o sin resultados en recall: %s", stderr)
            return []

        try:
            data = json.loads(stdout)
            # Engram puede devolver una lista directamente o un objeto con clave "results"
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            if isinstance(data, list):
                return data
            return []
        except json.JSONDecodeError as e:
            logger.warning("Error parseando JSON de Engram: %s", e)
            return []

    def get_context(self, query: str, limit: int = 5) -> str:
        """
        Recupera memorias y las formatea para inyectarlas en un prompt.

        Args:
            query: Texto de búsqueda.
            limit: Número máximo de resultados.

        Returns:
            String formateado con las memorias, o string vacío si no hay.
        """
        memories = self.recall(query, limit=limit)
        if not memories:
            return ""

        lines = ["=== MEMORIA RECUPERADA (Engram) ==="]
        for m in memories:
            content = m.get("content", "")
            if not content:
                continue
            # Limitar longitud para no saturar el prompt
            if len(content) > 500:
                content = content[:497] + "..."
            lines.append(f"- {content}")
        return "\n".join(lines)

    def stats(self) -> Optional[Dict[str, Any]]:
        """
        Obtiene estadísticas de la base de memoria.

        Returns:
            Diccionario con estadísticas, o None si falla.
        """
        if not self._available:
            return None

        cmd = ["stats", "--db", str(self.db_path), "--json"]
        success, stdout, _ = self._run_command(cmd)
        if not success or not stdout:
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None

    def forget(self, memory_id: str) -> bool:
        """
        Elimina una memoria específica por su ID.

        Args:
            memory_id: ID de la memoria a eliminar.

        Returns:
            True si se eliminó correctamente.
        """
        if not self._available:
            return False

        cmd = ["forget", memory_id, "--db", str(self.db_path)]
        success, _, _ = self._run_command(cmd)
        return success

    def is_available(self) -> bool:
        """Devuelve True si Engram está disponible y listo para usar."""
        return self._available

    # ============================================================
    # MÉTODOS PRIVADOS
    # ============================================================

    def _check_available(self) -> bool:
        """Verifica que el binario de Engram existe y es ejecutable."""
        return shutil.which(self.binary) is not None

    def _run_command(self, cmd: List[str], timeout: int = 10) -> tuple[bool, str, str]:
        """
        Ejecuta un comando de Engram de forma segura.

        Returns:
            (success, stdout, stderr)
        """
        if not self._available:
            return False, "", "Engram no disponible"

        full_cmd = [self.binary] + cmd
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
            logger.error("Binario Engram no encontrado: %s", self.binary)
            self._available = False
            return False, "", "Binario no encontrado"
        except Exception as e:
            logger.exception("Error ejecutando Engram: %s", e)
            return False, "", str(e)

    def _save_sync(
        self, content: str, tags: Optional[List[str]] = None, source: str = "aiclient"
    ) -> bool:
        """Implementación síncrona del guardado."""
        cmd = [
            "remember",
            content,
            "--db",
            str(self.db_path),
            "--source",
            source,
        ]
        if tags:
            cmd.extend(["--tags", ",".join(tags)])

        success, stdout, stderr = self._run_command(cmd)
        if not success:
            logger.debug("Error guardando memoria: %s", stderr or stdout)
        else:
            logger.debug("Memoria guardada correctamente: %s", content[:50])
        return success
