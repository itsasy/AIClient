import json
import logging
import os
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

    Utiliza los comandos CLI:
    - save <title> <msg>   → guardar memoria
    - search <query>       → buscar memorias
    - stats                → estadísticas
    - delete <obs_id>      → eliminar memoria

    La base de datos se almacena en el directorio definido por ENGRAM_DATA_DIR.
    Por defecto, usamos el directorio del proyecto (PROJECT_ROOT).
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        project: Optional[str] = None,
        async_save: bool = True,
    ):
        """
        Inicializa el cliente de Engram.

        Args:
            data_dir: Directorio donde Engram almacenará sus datos.
                     Por defecto, Config.PROJECT_ROOT / ".engram".
            project: Nombre del proyecto (para etiquetar memorias).
                     Por defecto, nombre del directorio actual.
            async_save: Si es True, guarda en hilo separado.
        """
        self.data_dir = data_dir or Path.home() / ".engram"
        self.project = project or Config.PROJECT_ROOT.name
        self.async_save = async_save

        # Establecer ENGRAM_DATA_DIR para que Engram use este directorio
        os.environ["ENGRAM_DATA_DIR"] = str(self.data_dir)

        # Verificar disponibilidad
        self._available = self._check_available()
        if not self._available:
            logger.warning(
                "Engram no está instalado o no se encuentra en el PATH. "
                "La memoria persistente estará desactivada. "
                "Instala con: brew install engram (o descarga el binario)."
            )
        else:
            logger.info("Engram disponible. Data dir: %s", self.data_dir)

    def _check_available(self) -> bool:
        """Verifica que el binario de Engram existe y es ejecutable."""
        return shutil.which("engram") is not None

    def _run_command(self, cmd: List[str], timeout: int = 10) -> tuple[bool, str, str]:
        """Ejecuta un comando de Engram de forma segura."""
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
        """
        Guarda una memoria en Engram.

        Args:
            content: Texto de la memoria.
            tags: Lista de etiquetas (se guardan como tipo/scope).
            source: Fuente (se añade al contenido).
            async_mode: Si es True, ejecuta en hilo separado.

        Returns:
            bool: True si se guardó correctamente (o se encoló).
        """
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
        """Implementación síncrona del guardado."""
        # Usar las primeras 50 palabras como título
        title = content[:50] + ("..." if len(content) > 50 else "")
        msg = content

        cmd = ["save", title, msg, "--project", self.project]
        if tags:
            # Engram usa --type y --scope. Usamos --type para la primera etiqueta y --scope para el resto.
            # O simplemente pasamos las etiquetas en el contenido.
            # Como no hay forma directa, añadimos las tags al contenido.
            msg_with_tags = f"[{', '.join(tags)}] {content}"
            cmd = ["save", title, msg_with_tags, "--project", self.project]

        success, stdout, stderr = self._run_command(cmd)
        if not success:
            logger.debug("Error guardando memoria: %s", stderr or stdout)
        else:
            logger.debug("Memoria guardada: %s", title)
        return success

    def recall(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Busca memorias en Engram.

        Args:
            query: Texto de búsqueda.
            limit: Número máximo de resultados.

        Returns:
            Lista de memorias, cada una con 'content', 'id' y 'score'.
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

        # Engram devuelve texto plano. Parseamos líneas que empiecen con número o bullet.
        # Ejemplo:
        #   1. Mi color favorito es el azul  (score: -0.45)
        #   2. Otro recuerdo
        results = []
        lines = stdout.splitlines()
        for line in lines:
            # Intentar extraer número y contenido
            import re

            match = re.match(r"\s*(\d+)\.\s+(.*?)(?:\s+\(score:\s*([\d.-]+)\))?$", line)
            if match:
                idx = int(match.group(1))
                content = match.group(2).strip()
                score_str = match.group(3)
                score = float(score_str) if score_str else 0.0
                results.append(
                    {
                        "id": str(idx),
                        "content": content,
                        "score": score,
                    }
                )
        return results

    def get_context(self, query: str, limit: int = 5) -> str:
        """Recupera memorias y las formatea para inyectarlas en un prompt."""
        memories = self.recall(query, limit=limit)
        if not memories:
            return ""

        lines = ["=== MEMORIA RECUPERADA (Engram) ==="]
        for m in memories:
            content = m.get("content", "")
            if not content:
                continue
            if len(content) > 500:
                content = content[:497] + "..."
            lines.append(f"- {content}")
        return "\n".join(lines)

    def stats(self) -> Optional[Dict[str, Any]]:
        """Obtiene estadísticas de Engram."""
        if not self._available:
            return None

        cmd = ["stats", "--project", self.project]
        success, stdout, _ = self._run_command(cmd)
        if not success or not stdout:
            return None

        # Parsear estadísticas (texto plano)
        # Ejemplo:
        #   Total memories: 42
        #   ...
        stats = {}
        for line in stdout.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                stats[key.strip()] = val.strip()
        return stats

    def forget(self, memory_id: str) -> bool:
        """
        Elimina una memoria por su ID (observación).
        """
        if not self._available:
            return False

        cmd = ["delete", memory_id, "--project", self.project]
        success, _, _ = self._run_command(cmd)
        return success

    def is_available(self) -> bool:
        return self._available
