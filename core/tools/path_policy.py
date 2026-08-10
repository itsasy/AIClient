from __future__ import annotations

from pathlib import Path
from typing import Optional

from core.config import Config


class PathPolicy:
    """
    Valida rutas de archivos para prevenir accesos no permitidos.

    Responsabilidades:
        - Verificar que la ruta esté dentro del proyecto.
        - Prevenir path traversal (.., rutas absolutas externas).
        - Normalizar rutas relativas.
    """

    @staticmethod
    def project_root() -> Path:
        return Config.TARGET_PROJECT_ROOT.resolve()

    @staticmethod
    def normalize(path: str | Path) -> Path:
        """Convierte a Path absoluto resuelto."""
        return Path(path).expanduser().resolve()

    @staticmethod
    def is_within_project(path: str | Path) -> bool:
        """Verifica que la ruta esté dentro del directorio del proyecto."""
        root = PathPolicy.project_root()
        target = PathPolicy.normalize(path)

        try:
            target.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def validate(path: str | Path) -> tuple[bool, Optional[str]]:
        """
        Valida la ruta y devuelve (ok, error_message).
        """
        if path is None or (isinstance(path, str) and not path.strip()):
            return False, "La ruta está vacía."

        raw = str(path).strip()

        # Bloqueo explícito de patrones de traversal antes de resolve
        # (útil para mensajes claros; resolve + relative_to es la garantía real)
        if raw.startswith("~") and ".." in raw:
            # se normaliza igual; no bloqueamos ~ legítimo
            pass

        try:
            normalized = PathPolicy.normalize(raw)
        except Exception as exc:
            return False, f"Ruta inválida: {exc}"

        if not PathPolicy.is_within_project(normalized):
            return (
                False,
                f"La ruta '{raw}' resuelve fuera del proyecto "
                f"({normalized}). Path traversal bloqueado.",
            )

        # Denegar escritura sobre el propio root del proyecto como archivo
        root = PathPolicy.project_root()
        if normalized == root:
            return False, "No se puede usar el directorio raíz del proyecto como archivo."

        return True, None

    @staticmethod
    def safe_join(*parts: str) -> Path:
        """
        Une partes bajo el root del proyecto y valida el resultado.
        """
        root = PathPolicy.project_root()
        candidate = root.joinpath(*parts)
        ok, err = PathPolicy.validate(candidate)
        if not ok:
            raise ValueError(err or "Ruta insegura")
        return PathPolicy.normalize(candidate)
